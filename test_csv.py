import pandas as pd
import re
import io

with open('/home/cstone/source/csc_554/data/flow02/flow02.csv', 'r') as f:
    content = f.read()

# Replace \\" (backslash-backslash-quote) with single quote
cleaned = re.sub(r'\\\\"', "'", content)

lines = cleaned.split('\n')
print("Cleaned line 7:")
print(repr(lines[6]))

# Count backslashes before quotes in cleaned line 7
line7 = lines[6]
for i, ch in enumerate(line7):
    if ch == '\\':
        print(f"Backslash at {i}, next char: {repr(line7[i+1])}")

# Try reading with different quoting options
try:
    df = pd.read_csv(io.StringIO(cleaned), engine='python', quotechar="'")
    print('Success with quotechar single quote! Shape:', df.shape)
except Exception as e:
    print(f'Error with quotechar single quote: {e}')

# Try reading without any quoting
try:
    df = pd.read_csv(io.StringIO(cleaned), engine='python', quoting=3, quotechar=None)
    print('Success with no quoting! Shape:', df.shape)
except Exception as e:
    print(f'Error with no quoting: {e}')
