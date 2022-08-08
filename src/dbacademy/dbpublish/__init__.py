import sys
sys.modules["dbacademy"] = __import__("dbacademy_courseware")

print("*" * 80)
print("* DEPRECATION WARNING")
print("* The package \"dbacademy.dbpublish\" has been moved to \"dbacademy_courseware.dbpublish\".")
print("*" * 80)
