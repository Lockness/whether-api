import asyncio
import aiohttp


class AsyncHelper:

    def __init__(self, url_id_list, headers):
        self.url_id_list = url_id_list
        self.headers = headers

    async def get_response(self, session, url):
        async with session.get(url) as response:
            data = await response.json()
        return data

    async def get_one(self, url_id):
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False), headers=self.headers) as session:
            url = url_id[0]
            marker = url_id[1]
            data = await self.get_response(session, url)
        return data, marker

    def async_all(self):
        loop = asyncio.get_event_loop()
        to_do = [self.get_one(url_id) for url_id in self.url_id_list]
        wait_coro = asyncio.wait(to_do)
        result, _ = loop.run_until_complete(wait_coro)
        return result
