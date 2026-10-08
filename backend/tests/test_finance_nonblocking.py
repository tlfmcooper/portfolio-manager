import asyncio
import threading
import pytest
from app.services.finance_service import FinanceService


@pytest.mark.asyncio
async def test_slow_yahoo_info_does_not_block_other_coroutines(monkeypatch):
    started, release = threading.Event(), threading.Event()
    class Stock:
        @property
        def info(self):
            started.set()
            assert release.wait(timeout=1), 'Event loop was blocked by Yahoo work'
            return {'symbol': 'AAA', 'currentPrice': 100, 'longName': 'AAA'}
    monkeypatch.setattr('app.services.finance_service.yf.Ticker', lambda ticker: Stock())
    task = asyncio.create_task(FinanceService.get_asset_info('AAA', 'stock'))
    await asyncio.to_thread(started.wait, 1)
    release.set()
    result = await task
    assert result['current_price'] == 100
