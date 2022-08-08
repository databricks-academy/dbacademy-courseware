import sys
import dbacademy
import dbacademy_courseware

print("-"*80)
help(dbacademy)
print("-"*80)
help(dbacademy_courseware)

print("-"*80)
for module in sys.modules:
    if module.startswith("d"):
        print(module)

print("-"*80)
