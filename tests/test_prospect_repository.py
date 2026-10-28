import pytest

from app.main import app
from app.database.mongodb import connect_to_mongodb, close_mongodb_connection
from app.repositories.prospect_repository import ProspectRepository


@pytest.mark.anyio
async def test_prospect_repository_count():
    await connect_to_mongodb()

    try:
        repository = ProspectRepository()

        count = await repository.count()

        print("Existing Prospect Count:", count)

        assert count >= 0

    finally:
        await close_mongodb_connection()