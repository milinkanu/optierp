import pandas as pd
from pathlib import Path
p = Path(r'c:\Users\Milin\Desktop\OptiReach\optierp4\FinOps_DataStructure.xlsx')
xl = pd.ExcelFile(p)
print('sheets=', xl.sheet_names)
for sheet in xl.sheet_names:
    print('\n===', sheet)
    df = xl.parse(sheet)
    print(df.head(40).to_string(index=False))
