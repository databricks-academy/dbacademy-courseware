import dbacademy
dbacademy.dbtest = __import__("dbacademy_courseware.dbtest")
dbacademy.dbtest.TestConfig = __import__("dbacademy_courseware.dbtest.TestConfig")

print("*" * 80)
print("* DEPRECATION WARNING")
print("* The package \"dbacademy.dbtest\" has been moved to \"dbacademy_courseware.dbtest\".")
print("*" * 80)
