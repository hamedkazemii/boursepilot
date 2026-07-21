from dataclasses import dataclass


@dataclass
class Fund:

    symbol: str
    name: str
    ins_code: str
    fund_type: str = ""
    active: bool = True
    description: str = ""
