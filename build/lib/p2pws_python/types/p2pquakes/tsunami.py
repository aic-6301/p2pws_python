from .basicdata import BasicData
from typing import Literal

class TsunamiIssue:
    """発信元の情報です。"""
    source: str
    """発表元"""
    time: str
    """発表日時"""
    _type: str
    """発表種別。現在はFocus(津波予報)のみ。"""
    
    def __init__( self, data: dict ) -> None:
        self.source = data["source"]
        self.time = data["time"]
        self._type = data["type"]
    
class FirstHeight:
    """津波の到達予想時刻"""
    arrivalTime: str
    """第一波の到達予想時刻"""
    condition: Literal["ただちに津波来襲と予測", "津波到達中と推測", "第１波の到達を確認"]
    
    def __init__( self, data: dict ) -> None:
        self.arrivalTime = data["arrivalTime"]
        self.condition = data.get("condition", None)
    
class MaxHeight:
    """予想される津波の高さ"""
    description: str
    """高さの文字列表現"""
    value: float
    """高さの数値表現"""
    
    def __init__( self, data: dict ) -> None:
        self.description = data["description"]
        self.value = data["value"]
    
class TsunamiArea:
    """津波予報の地域情報です。"""
    grade: Literal["MajorWarning", "Warning", "Watch", "Unknown"]
    """津波予報の種類"""
    immediate: bool
    """直ちに津波が来襲すると予想されているかどうか"""
    name: str
    """津波予報区名"""
    firstHeight: FirstHeight
    maxHeight: MaxHeight
    
    def __init__( self, data: dict ) -> None:
        self.grade = data["grade"]
        self.immediate = data["immediate"]
        self.name = data["name"]
        self.firstHeight = FirstHeight(data["firstHeight"])
        self.maxHeight = MaxHeight(data["maxHeight"])

class Tsunami ( BasicData ):
    """
    津波予報の内容です。
    """
    _id: str
    code: 552
    """
    情報コードは常に552です。
    """
    time: str
    """
    受信日時。
    """
    cancelled: bool
    """
    キャンセル報かどうか。
    trueの場合、areasの値は空配列になります。
    """
    issue: TsunamiIssue
    """
    配信元の情報
    """
    areas: list[TsunamiArea] | None
    """
    津波予報の詳細
    """

    def __init__( self, data: dict ) -> None:
        super().__init__(data)
        self._id = data["_id"] or data["id"]
        self.code = data["code"]
        self.cancelled = data["cancelled"]
        self.issue = TsunamiIssue(data["issue"])
        self.areas = [TsunamiArea(area) for area in data.get("areas", [])] if data.get("areas") else None