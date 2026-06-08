from agents.money_trail import detect_laundering_patterns

mock_hops = [
  {"hop": 1, "amount_usd": 75000, "date": "2024-01-01T00:00:00+00:00",
   "from_address": "0xAAA", "to_address": "0xBBB", "tx_hash": "0x1"},
  {"hop": 2, "amount_usd": 30000, "date": "2024-01-01T12:00:00+00:00",
   "from_address": "0xBBB", "to_address": "0xCCC", "tx_hash": "0x2"},
  {"hop": 3, "amount_usd": 30000, "date": "2024-01-02T06:00:00+00:00",
   "from_address": "0xCCC",
   "to_address": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
   "tx_hash": "0x3"},
]

result = detect_laundering_patterns(mock_hops)
print(result)
