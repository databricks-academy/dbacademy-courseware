import sys
import dbacademy
import dbacademy_courseware

print("-"*80)
help(dbacademy)
print("-"*80)
help(dbacademy_courseware)

print("-"*80)
module = sys.modules["dbacademy"]
print(type(module))

print("-"*80)
