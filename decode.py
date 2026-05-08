from urllib.parse import urlparse, parse_qs, unquote

url = input("DrbDooE3sMDsEiApegkxv5kDI7gYUfcUkaqLUJNhn1U9uVb3_9Kbv9z_FSrXDgKpg_Tz7aIuxd9vG0vIKKSK_-lWfSBTJshttxSsJmsLNSiPu1dy0JmS1WYeHmjHMjAbzjZLhKC7NB8kHEXM61oQFoFH8YkTFGDmb0y0bQSFgTFRw8bneG9R-Gtsjc6NaSVkvH-XEMC4iGMCS_6g0zVJMrYpBCCG00QDeBn3b653FmaNZrM8qsOey617M_X5fCH3T0xS_3HfXVvPsUvU%2Av%216896.s1\n")

parsed = urlparse(url)

code = parse_qs(parsed.query)["code"][0]

decoded = unquote(code)

print("\nDECODED CODE:\n")
print(decoded)