

from services.live_scanner import LiveScanner


scanner = LiveScanner()


data = scanner.scan()


print(
    "Funds:",
    len(data)
)


assert isinstance(
    data,
    list
)


print(
    "LIVE SCANNER OK"
)

