from pathlib import Path
import json


LIVE = Path("data/sync/live/latest.json")
OLD = Path("data/sync/live/previous.json")

OUT = Path("data/sync/delta/latest_delta.json")


def build_delta():

    if not LIVE.exists():
        raise RuntimeError(
            "latest.json missing"
        )


    current = json.loads(
        LIVE.read_text()
    )


    if not OLD.exists():

        OLD.write_text(
            json.dumps(
                current,
                ensure_ascii=False
            )
        )

        print(
            "FIRST SNAPSHOT - FULL REQUIRED"
        )

        return None


    previous = json.loads(
        OLD.read_text()
    )


    old_map = {
        x.get("l18"): x
        for x in previous["symbols"]
    }


    changed=[]


    for item in current["symbols"]:

        symbol=item.get("l18")

        if old_map.get(symbol)!=item:
            changed.append(item)


    delta={
        "created_at":current["created_at"],
        "count":len(changed),
        "symbols":changed
    }


    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT.write_text(
        json.dumps(
            delta,
            ensure_ascii=False,
            indent=2
        )
    )


    OLD.write_text(
        json.dumps(
            current,
            ensure_ascii=False
        )
    )


    print(
        "DELTA CREATED changed=",
        len(changed)
    )


if __name__=="__main__":
    build_delta()
