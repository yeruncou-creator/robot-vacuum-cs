import os.path
from utils.logger_handler import logger
from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService
import random
from utils.config_handler import agent_conf
from utils.path_tool import get_abs_path
import requests

rag = RagSummarizeService()

user_ids = ["1001", "1002", "1003", "1004", "1005", "1006", "1007", "1008", "1009", "1010"]
month_arr = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"]

external_data = {}

@tool(description="从向量存储中检索参考资料")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)

@tool(description="获取指定城市的实时天气，返回温度、湿度、风速和降水等信息")
def get_weather(city: str) -> str:
    """通过 Open-Meteo 获取城市当前天气。"""
    try:
        # 1. 将城市名称转换成经纬度
        geo_response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1,
                "language": "zh",
                "format": "json",
            },
            timeout=10,
        )
        geo_response.raise_for_status()

        places = geo_response.json().get("results", [])
        if not places:
            return f"没有找到城市：{city}"

        place = places[0]
        latitude = place["latitude"]
        longitude = place["longitude"]
        city_name = place["name"]

        # 2. 查询当前天气
        weather_response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "apparent_temperature,"
                    "precipitation,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "timezone": "auto",
            },
            timeout=10,
        )
        weather_response.raise_for_status()

        current = weather_response.json()["current"]

        # 3. 整理成大模型容易理解的字符串
        return (
            f"城市：{city_name}\n"
            f"数据时间：{current['time']}\n"
            f"气温：{current['temperature_2m']}°C\n"
            f"体感温度：{current['apparent_temperature']}°C\n"
            f"相对湿度：{current['relative_humidity_2m']}%\n"
            f"当前降水量：{current['precipitation']} mm\n"
            f"风速：{current['wind_speed_10m']} km/h\n"
            f"天气代码：{current['weather_code']}"
        )

    except requests.RequestException as e:
        return f"天气 API 请求失败：{type(e).__name__}"
    except (ValueError, KeyError, IndexError):
        return "天气数据解析失败，请稍后重试。"

@tool(description="获取当前用户所在的城市名称（基于IP定位），以纯字符串形式返回")
def get_user_location() -> str:
    """通过 IP 定位获取用户当前所在城市（用户未指定城市时，配套 get_weather 使用）。"""
    try:
        resp = requests.get(
            "http://ip-api.com/json/",
            params={"lang": "zh-CN"},
            timeout=10,
        )
        resp.raise_for_status()

        data = resp.json()
        if data.get("status") != "success":
            return f"定位失败：{data.get('message', '未知原因')}"

        # city 可能为空（部分 IP 段只能定位到省级），退回用省份名
        return data.get("city") or data.get("regionName") or "未知位置"
    except requests.RequestException as e:
        return f"IP 定位请求失败：{type(e).__name__}"

@tool(description="获取用户ID,以纯字符串形式返回")
def get_user_id() -> str:
    return random.choice(user_ids)

@tool(description="获取当前月份，以纯字符串形式返回")
def get_current_month() -> str:
    return random.choice(month_arr)

def generate_external_data():
    """
    {
        "user_id" : {
            "month" : {"特征": XXX, "效率": XXX, ...}
            "month" : {"特征": XXX, "效率": XXX, ...}
            "month" : {"特征": XXX, "效率": XXX, ...}
            ...
        },
        "user_id" : {
            "month" : {"特征": XXX, "效率": XXX, ...}
            "month" : {"特征": XXX, "效率": XXX, ...}
            "month" : {"特征": XXX, "效率": XXX, ...}
            ...
        },
        "user_id" : {
            "month" : {"特征": XXX, "效率": XXX, ...}
            "month" : {"特征": XXX, "效率": XXX, ...}
            "month" : {"特征": XXX, "效率": XXX, ...}
            ...
        },
        ...
    }
    :return:
    """
    if not external_data:
        external_data_path = get_abs_path(agent_conf["external_data_path"])

        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件{external_data_path}不存在")

        with open(external_data_path, "r", encoding="utf-8") as f:
            for line in f.readlines()[1:]:
                arr: list[str] = line.strip().split(",")

                user_id: str = arr[0].replace('"', "")
                feature: str = arr[1].replace('"', "")
                efficiency: str = arr[2].replace('"', "")
                consumables: str = arr[3].replace('"', "")
                comparison: str = arr[4].replace('"', "")
                time: str = arr[5].replace('"', "")

                if user_id not in external_data:
                    external_data[user_id] = {}

                external_data[user_id][time] = {
                    "特征": feature,
                    "效率": efficiency,
                    "消耗": consumables,
                    "对比": comparison
                }


@tool(description="从外部系统中获取指定用户在指定月份的使用记录，以纯字符串形式返回，如果未检索到返回空字符串")
def fetch_external_data(user_id: str, month: str) -> str:
    generate_external_data()

    try:
        return external_data[user_id][month]
    except KeyError:
        logger.warning(f"[fetch_external_data]未能检索到用户： {user_id}在{month}的使用记录")
        return ""

@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    return "fill_context_for_report已调用"