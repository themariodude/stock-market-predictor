from collections.abc import Generator

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_session
from app.services.auth import (
    TOKEN_TTL_SECONDS,
    AuthenticationError,
    DuplicateAccountError,
    RegisteredInvestor,
    authenticate_investor,
    create_access_token,
    register_investor,
    verify_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# Database session dependency
def get_db() -> Generator[Session, None, None]:
    """Provide a database session and close it after the request."""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


class RegisterRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
        pattern=r".*\S.*",
    )
    email: str = Field(
        min_length=3,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class AccountResponse(BaseModel):
    email: str
    name: str
    saved_stocks: list[str]
    investment_focus: str


class RegisterResponse(BaseModel):
    email: str
    name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AccountResponse


def _account_response(investor: RegisteredInvestor) -> AccountResponse:
    return AccountResponse(
        email=investor.email,
        name=investor.name,
        saved_stocks=list(investor.saved_stocks),
        investment_focus=investor.investment_focus,
    )


def _unauthorized(detail: str = "Authentication required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _investor_from_authorization(
    authorization: str | None,
    db: Session,
) -> RegisteredInvestor:
    """Retrieve the authenticated investor from a bearer token."""
    if not authorization:
        raise _unauthorized()

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("A bearer token is required.")

    try:
        return verify_access_token(token, db=db)
    except AuthenticationError as exc:
        raise _unauthorized(str(exc)) from exc


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    credentials: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Register a new investor account."""
    try:
        user = register_investor(
            db=db,
            name=credentials.name,
            email=credentials.email,
            password=credentials.password,
        )
    except DuplicateAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return RegisterResponse(
        email=user.email,
        name=user.name,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate a registered investor and return a bearer token."""
    try:
        investor = authenticate_investor(
            credentials.email,
            credentials.password,
            db=db,
        )
    except AuthenticationError as exc:
        raise _unauthorized(str(exc)) from exc

    return LoginResponse(
        access_token=create_access_token(investor.email),
        expires_in=TOKEN_TTL_SECONDS,
        user=_account_response(investor),
    )


@router.get("/me", response_model=AccountResponse)
def current_account(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AccountResponse:
    """Return saved account information for the authenticated investor."""
    investor = _investor_from_authorization(authorization, db)
    return _account_response(investor)
