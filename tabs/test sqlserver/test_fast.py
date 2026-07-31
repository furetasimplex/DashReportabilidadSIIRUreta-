from sqlalchemy import text
engine = get_engine()
with engine.connect() as cx:
    print(cx.execute(text("SELECT @@VERSION")).scalar())