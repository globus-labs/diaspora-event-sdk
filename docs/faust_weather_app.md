# Topic: Use [faust](https://faust-streaming.github.io/faust/) to Process Records
## Producer Code
[faust_produce.py](docs/faust_produce.py)
## Consumer Code
[faust_consume.py](docs/faust_consume.py)

## Record Example
```json
{
  "latitude": 41.85271,
  "longitude": -87.653625,
  "generationtime_ms": 0.03707408905029297,
  "utc_offset_seconds": 0,
  "timezone": "GMT",
  "timezone_abbreviation": "GMT",
  "elevation": 179,
  "current_units": {
    "time": "iso8601",
    "interval": "seconds",
    "temperature_2m": "°C",
    "relative_humidity_2m": "%"
  },
  "current": {
    "time": "2023-12-27T18:45",
    "interval": 900,
    "temperature_2m": 5.4,
    "relative_humidity_2m": 71
  },
  "minutely_15_units": {
    "time": "iso8601",
    "temperature_2m": "°C",
    "relative_humidity_2m": "%"
  },
  "minutely_15": {
    "time": ["2023-12-27T00:00", "2023-12-27T00:15", ...],
    "temperature_2m": [3.1, 2.6, ...],
    "relative_humidity_2m": [85, 84, ...]
  },
  "location": "Chicago",
  "fetch_GMT": [2023, 12, 27, 18, 48, 4, 2, 361, 0]
}

```

## Record Class
```python
class CurrentUnits(faust.Record, serializer="json"):
    time: str
    interval: str
    temperature_2m: str
    relative_humidity_2m: str


class Current(faust.Record, serializer="json"):
    time: str
    interval: int
    temperature_2m: float
    relative_humidity_2m: int


class Minutely15Units(faust.Record, serializer="json"):
    time: str
    temperature_2m: str
    relative_humidity_2m: str


class Minutely15(faust.Record, serializer="json"):
    time: list[str]
    temperature_2m: list[float]
    relative_humidity_2m: list[int]


class Record(faust.Record, serializer="json"):
    latitude: float
    longitude: float
    generationtime_ms: float
    utc_offset_seconds: int
    timezone: str
    timezone_abbreviation: str
    elevation: int
    current_units: CurrentUnits
    current: Current
    minutely_15_units: Minutely15Units
    minutely_15: Minutely15
    location: str
    fetch_GMT: list[int]
```
