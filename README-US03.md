# US-03 — View Current Stock Information

Implements the backend service for retrieving recent stock information:

- Current price
- Previous close
- Price change
- Percentage change
- Trading volume

## File locations

- `backend/app/services/current_stock_info.py`
- `backend/tests/test_current_stock_info.py`

## Install dependencies

```bash
pip install -r backend/requirements-us03.txt
```

## Run tests

From the `backend` directory:

```bash
pytest tests/test_current_stock_info.py
```

## Example usage

```python
from app.services.current_stock_info import get_current_stock_info

result = get_current_stock_info("LMT")
print(result)
```
