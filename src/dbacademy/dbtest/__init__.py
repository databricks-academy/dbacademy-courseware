import sys
print(f"[[[ {__name__} ]]]")
sys.modules["dbacademy.dbtest"] = __import__("dbacademy_courseware.dbtest")

print("*" * 80)
print("* DEPRECATION WARNING")
print("* The package \"dbacademy.dbtest\" has been moved to \"dbacademy_courseware.dbtest\".")
print("*" * 80)
