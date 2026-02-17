import asyncio

from ui.utils.search_index_service import SearchIndexService


async def main():
    svc = SearchIndexService()
    svc.build_and_cache_index()


asyncio.run(main())
