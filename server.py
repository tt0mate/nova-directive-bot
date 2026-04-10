from aiohttp import web
import asyncio

async def health_check(request):
    return web.Response(text='Bot rodando via deploy. Ambiente local ativo.')

async def main():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print('Servidor local ativo. Bot Discord rodando via deploy.')
    await asyncio.Event().wait()

asyncio.run(main())
