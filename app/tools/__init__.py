"""Tools: Google Sheets + Amazon SNS (SMS). Local @tool for MVP, migrate to Gateway MCP in P4 (§8.7, §16 D1).

SMS backend: app/tools/sms.py (boto3 SNS) — replaces Twilio. app/tools/twilio.py is kept as a
compatibility shim for any code still using the old import path.
"""
