import sqlite3
import pandas as pd
import statsmodels.formula.api as smf

# Wczytanie skryptu SQL
with open("NAC_results_sqlite_fixed.sql", "r", encoding="utf-8") as file:
    sql_script = file.read()

# Utworzenie bazy danych SQLite w pamięci
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# Ręczne tworzenie tabel, aby uniknąć błędów ze skryptu
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

for command in sql_script.split(';'):
    command = command.strip()
    if command:
        try:
            cursor.execute(command)
        except Exception as e:
            print(f"Błąd w zapytaniu:\n{command[:50]}...\n{e}\n")

# Wczytanie danych do pandas
df_wyniki = pd.read_sql_query("SELECT * FROM wyniki", conn)
conn.close()

#wczytanie danych z pliku CSV
df_ankieta_details = pd.read_excel("NAC_ankieta_update.xlsx")

#usunięcie zbędnej kolumny
df_ankieta_details = df_ankieta_details.drop(columns=['Unnamed: 31'])

#agregacja danych do obliczenia 'win_ratio'
wins_count = df_wyniki.groupby('winner').size().reset_index(name='wins')
wins_count.rename(columns={'winner': 'Image ID'}, inplace=True)

left_id_counts = df_wyniki['left_id'].value_counts()
right_id_counts = df_wyniki['right_id'].value_counts()
total_comparisons = (left_id_counts.add(right_id_counts, fill_value=0)).reset_index(name='total_comparisons')
total_comparisons.rename(columns={'index': 'Image ID'}, inplace=True)

df_aggregated_results = pd.merge(total_comparisons, wins_count, on='Image ID', how='left')
df_aggregated_results['wins'] = df_aggregated_results['wins'].fillna(0).astype(int)
df_aggregated_results['win_ratio'] = df_aggregated_results['wins'] / df_aggregated_results['total_comparisons']

# połączenie danych w jeden data frame
final_df = pd.merge(df_ankieta_details, df_aggregated_results, on='Image ID', how='left')

# usunięcie wierszy z brakującymi wartościami 'win_ratio'
df_analysis = final_df.dropna(subset=['win_ratio']).copy()

#analiza mediacji: Zmienna niezależna (X) = 'Areola a', mediator (M) = 'Areola to Nipple delta E', zmienna zależna (Y) = 'win_ratio'
print("Analiza mediacji: Y ~ X z M jako mediatorem")
print("X = Areola a, M = Areola to Nipple delta E, Y = win_ratio")

# regresja Y na X
model_1 = smf.ols('win_ratio ~ Q("Areola a")', data=df_analysis).fit()
print("\n--- Model 1: Y na X ---")
print(model_1.summary())

# regresja M na X
model_2 = smf.ols('Q("Areola to Nipple delta E") ~ Q("Areola a")', data=df_analysis).fit()
print("\n--- Model 2: M na X ---")
print(model_2.summary())

# regresja Y na X i M
model_3 = smf.ols('win_ratio ~ Q("Areola a") + Q("Areola to Nipple delta E")', data=df_analysis).fit()
print("\n--- Model 3: Y na X i M ---")
print(model_3.summary())

# analiza moderacji: Zmienna niezależna (X) = 'Areola a', moderator (Mod) = 'Nipple to areola ratio', zmienna zależna (Y) = 'win_ratio'
print("\n\n### Analiza moderacji: Y ~ X z Mod jako moderatorem")
print("### X = Areola a, Mod = Nipple to areola ratio, Y = win_ratio")

# utworzenie terminu interakcji i regresja Y na X, Mod oraz interakcję
model_4 = smf.ols('win_ratio ~ Q("Areola a") * Q("Nipple to areola ratio")', data=df_analysis).fit()
print("\n--- Model 4: Y na X, Mod oraz termin interakcji ---")
print(model_4.summary())
