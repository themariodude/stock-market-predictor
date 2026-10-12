from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.services.auth import (
    TOKEN_TTL_SECONDS,
    AuthenticationError,
    RegisteredInvestor,
    authenticate_investor,
    create_access_token,
    verify_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class AccountResponse(BaseModel):
    email: str
    name: str
    saved_stocks: list[str]
    investment_focus: str


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


def _investor_from_authorization(authorization: str | None) -> RegisteredInvestor:
    if not authorization:
        raise _unauthorized()

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("A bearer token is required.")

    try:
        return verify_access_token(token)
    except AuthenticationError as exc:
        raise _unauthorized(str(exc)) from exc


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest) -> LoginResponse:
    """Authenticate a registered investor and return a bearer token."""
    try:
        investor = authenticate_investor(credentials.email, credentials.password)
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
) -> AccountResponse:
    """Return saved account information for the authenticated investor."""
    investor = _investor_from_authorization(authorization)
    return _account_response(investor)
