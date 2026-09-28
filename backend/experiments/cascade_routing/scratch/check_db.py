import sqlite3
con = sqlite3.connect("cascade.db", timeout=10)
print("total:", con.execute("select count(*) from responses").fetchone())
print("with_qwen:", con.execute("select count(*) from responses where qwen_response is not null").fetchone())
print("with_gemini_ok:", con.execute("select count(*) from responses where gemini_response is not null and gemini_response not like '__GEMINI_ERROR__%'").fetchone())
for r in con.execute("select id, substr(prompt,1,60), length(qwen_response), substr(gemini_response,1,50) from responses order by id desc limit 5").fetchall():
    print(r)
