import sys

dbacademy = sys.modules["dbacademy"]
dbacademy["dbpublish"] = __import__("dbacademy_courseware.dbpublish")

print("*" * 80)
print("* DEPRECATION WARNING")
print("* The package \"dbacademy.dbpublish\" has been moved to \"dbacademy_courseware.dbpublish\".")
print("*" * 80)
