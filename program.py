import sqlite3
import pandas as pd

#wczytanie wyników sqla do bazy
with open("NAC_results_sqlite_fixed.sql", "r", encoding="utf-8") as file:
    sql_script = file.read()

#utworzenie bazy SQLite w RAM ---
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE ankiety (
  id VARCHAR(50) PRIMARY KEY,
  wiek VARCHAR(10),
  kod VARCHAR(10),
  plec VARCHAR(10)
);
""")

cursor.execute("""
CREATE TABLE wyniki (
  id VARCHAR(50),
  left_id VARCHAR(10),
  right_id VARCHAR(10),
  winner VARCHAR(10),
  numer INT,
  FOREIGN KEY (id) REFERENCES ankiety(id)
);
""")

# Wykonanie kwerend SQL 
for command in sql_script.split(";"):
    command = command.strip()
    if command:
        try:
            cursor.execute(command)
        except Exception as e:
            print(f"⚠️ Błąd w zapytaniu:\n{command[:100]}...\n{e}\n")

#wczytanie danych do pandas
df_ankiety = pd.read_sql_query("SELECT * FROM ankiety", conn)
df_wyniki = pd.read_sql_query("SELECT * FROM wyniki", conn)

df = pd.merge(df_wyniki, df_ankiety, on="id", how="left")
df["wiek"] = pd.to_numeric(df["wiek"], errors="coerce")

# --- KROK 5: Wyświetlenie wyników ---
print("Pierwsze wiersze z tabeli 'ankiety':")
print(df_ankiety.head())

print("\nPierwsze wiersze z tabeli 'wyniki':")
print(df_wyniki.head())

print("\nPołączone dane (wyniki + dane uczestnika):")
print(df.head())

print("\n Średni wiek uczestników wg płci:")
print(df.groupby("plec")["wiek"].mean())

# --- KROK 6: Zamknięcie bazy ---
conn.close()
