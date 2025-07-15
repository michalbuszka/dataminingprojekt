import sqlite3
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


# Wczytanie skryptu SQL
try:
    with open("NAC_results_sqlite_fixed.sql", "r", encoding="utf-8") as file:
        sql_script = file.read()
    print("Skrypt SQL załadowany pomyślnie.")
except FileNotFoundError:
    print("Błąd: Plik 'NAC_results_sqlite_fixed.sql' nie został znaleziony. Upewnij się, że jest w tym samym katalogu.")
    exit()
except Exception as e:
    print(f"Błąd podczas ładowania skryptu SQL: {e}")
    exit()

# Utworzenie bazy danych SQLite w pamięci
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()
print("Baza danych SQLite utworzona w pamięci.")

# Ręczne tworzenie tabel, aby uniknąć błędów ze skryptu (jeśli skrypt SQL miałby problem z DROP TABLE IF EXISTS)
try:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ankiety (
        id VARCHAR(50) PRIMARY KEY,
        wiek VARCHAR(10),
        kod VARCHAR(10),
        plec VARCHAR(10)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wyniki (
        id VARCHAR(50),
        left_id VARCHAR(10),
        right_id VARCHAR(10),
        winner VARCHAR(10),
        numer INT,
        FOREIGN KEY (id) REFERENCES ankiety(id)
    );
    """)
    print("Tabele 'ankiety' i 'wyniki' zostały utworzone (lub istniały).")
except sqlite3.Error as e:
    print(f"Błąd podczas tworzenia tabel SQLite: {e}")
    conn.close()
    exit()

# Wykonanie komend ze skryptu SQL (wstawianie danych)
print("Wstawianie danych do bazy danych SQLite...")
for command in sql_script.split(';'):
    command = command.strip()
    if command and not command.startswith("CREATE TABLE"): # Pomiń CREATE TABLE, bo już je utworzyliśmy
        try:
            cursor.execute(command)
        except Exception as e:
            # Drukuj tylko fragment komendy, jeśli jest długa
            print(f"Błąd w zapytaniu:\n{command[:100]}...\n{e}\n")
conn.commit() # Zapisz zmiany
print("Dane zostały wstawione do bazy danych.")

# Wczytanie danych z bazy danych do pandas
df_wyniki = pd.read_sql_query("SELECT * FROM wyniki", conn)
conn.close()
print(f"Wczytano {len(df_wyniki)} rekordów z tabeli 'wyniki'.")

# Wczytanie danych z pliku Excel
try:
    df_ankieta_details = pd.read_excel("NAC_ankieta_update.xlsx")
    print(f"Wczytano {len(df_ankieta_details)} rekordów z pliku 'NAC_ankieta_update.xlsx'.")
except FileNotFoundError:
    print("Błąd: Plik 'NAC_ankieta_update.xlsx' nie został znaleziony. Upewnij się, że jest w tym samym katalogu.")
    exit()
except Exception as e:
    print(f"Błąd podczas ładowania pliku Excel: {e}")
    exit()

# Usunięcie zbędnej kolumny
if 'Unnamed: 31' in df_ankieta_details.columns:
    df_ankieta_details = df_ankieta_details.drop(columns=['Unnamed: 31'])
    print("Usunięto kolumnę 'Unnamed: 31'.")
else:
    print("Kolumna 'Unnamed: 31' nie istnieje, pominięto usuwanie.")


# Agregacja danych do obliczenia 'win_ratio'
print("Obliczanie 'win_ratio'...")
wins_count = df_wyniki.groupby('winner').size().reset_index(name='wins')
wins_count.rename(columns={'winner': 'Image ID'}, inplace=True)

left_id_counts = df_wyniki['left_id'].value_counts()
right_id_counts = df_wyniki['right_id'].value_counts()
total_comparisons = (left_id_counts.add(right_id_counts, fill_value=0)).reset_index(name='total_comparisons')
total_comparisons.rename(columns={'index': 'Image ID'}, inplace=True)

df_aggregated_results = pd.merge(total_comparisons, wins_count, on='Image ID', how='left')
df_aggregated_results['wins'] = df_aggregated_results['wins'].fillna(0).astype(int)
df_aggregated_results['win_ratio'] = df_aggregated_results['wins'] / df_aggregated_results['total_comparisons']
print("Obliczono 'win_ratio' dla każdego obrazu.")

# Połączenie danych w jeden data frame
final_df = pd.merge(df_ankieta_details, df_aggregated_results, on='Image ID', how='left')
print(f"Połączono dane: final_df ma {len(final_df)} wierszy.")

# Usunięcie wierszy z brakującymi wartościami 'win_ratio'
df_analysis = final_df.dropna(subset=['win_ratio']).copy()
print(f"Usunięto wiersze z brakującymi 'win_ratio'. Do analizy pozostało {len(df_analysis)} wierszy.")

# Analiza
print("\n--- 2. Analiza statystyczna (Mediacja i Moderacja) ---")

# Analiza mediacji: Zmienna niezależna (X) = 'Areola a', mediator (M) = 'Areola to Nipple delta E', zmienna zależna (Y) = 'win_ratio'
print("\nAnaliza mediacji: Y ~ X z M jako mediatorem")
print("X = Areola a, M = Areola to Nipple delta E, Y = win_ratio")

# Regresja Y na X
model_1 = smf.ols('win_ratio ~ Q("Areola a")', data=df_analysis).fit()
print("\n--- Model 1: Y na X ---")
print(model_1.summary())

# Regresja M na X
model_2 = smf.ols('Q("Areola to Nipple delta E") ~ Q("Areola a")', data=df_analysis).fit()
print("\n--- Model 2: M na X ---")
print(model_2.summary())

# Regresja Y na X i M
model_3 = smf.ols('win_ratio ~ Q("Areola a") + Q("Areola to Nipple delta E")', data=df_analysis).fit()
print("\n--- Model 3: Y na X i M ---")
print(model_3.summary())

# Analiza moderacji: Zmienna niezależna (X) = 'Areola a', moderator (Mod) = 'Nipple to areola ratio', zmienna zależna (Y) = 'win_ratio'
print("\n\n### Analiza moderacji: Y ~ X z Mod jako moderatorem")
print("### X = Areola a, Mod = Nipple to areola ratio, Y = win_ratio")

# Utworzenie terminu interakcji i regresja Y na X, Mod oraz interakcję
model_4 = smf.ols('win_ratio ~ Q("Areola a") * Q("Nipple to areola ratio")', data=df_analysis).fit()
print("\n--- Model 4: Y na X, Mod oraz termin interakcji ---")
print(model_4.summary())

#wykresy

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = [12, 8]
plt.rcParams['figure.autolayout'] = True # Automatyczne dopasowanie układu, aby etykiety się nie nakładały

# Wykres 1: win_ratio vs Areola a (Y vs X)
plt.figure(figsize=(10, 6))
sns.regplot(x=df_analysis['Areola a'], y=df_analysis['win_ratio'], scatter_kws={'alpha':0.6}, line_kws={'color':'red'})
plt.title('Zależność Win Ratio od Areola a (Model 1)')
plt.xlabel('Areola a')
plt.ylabel('Win Ratio')
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout() # Dopasuj układ
plt.show()

# Wykres 2: Areola to Nipple delta E vs Areola a (M vs X)
plt.figure(figsize=(10, 6))
sns.regplot(x=df_analysis['Areola a'], y=df_analysis['Areola to Nipple delta E'], scatter_kws={'alpha':0.6}, line_kws={'color':'red'})
plt.title('Zależność Areola to Nipple delta E od Areola a (Model 2)')
plt.xlabel('Areola a')
plt.ylabel('Areola to Nipple delta E')
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout() # Dopasuj układ
plt.show()

# Wykres 3: win_ratio vs Areola a z uwzględnieniem Areola to Nipple delta E (Y vs X z M)

plt.figure(figsize=(10, 6))
sns.scatterplot(x=df_analysis['Areola a'], y=df_analysis['win_ratio'], hue=df_analysis['Areola to Nipple delta E'], palette='viridis', alpha=0.7)
plt.title('Zależność Win Ratio od Areola a (kolor: Areola to Nipple delta E) (Model 3)')
plt.xlabel('Areola a')
plt.ylabel('Win Ratio')
plt.legend(title='Areola to Nipple delta E', bbox_to_anchor=(1.05, 1), loc='upper left') # Legenda na zewnątrz
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout() # Dopasuj układ
plt.show()

# wykres interakcji, pokazujący linie regresji dla różnych poziomów moderatora
# (dla 10. i 90. percentyla)
plt.figure(figsize=(10, 6))

# Rysowanie wszystkich punktów jako szarych
plt.scatter(df_analysis['Areola a'], df_analysis['win_ratio'], alpha=0.2, color='grey', label='Wszystkie punkty')

# Obliczanie wartości dla niskiego i wysokiego poziomu moderatora
low_mod = df_analysis['Nipple to areola ratio'].quantile(0.1)
high_mod = df_analysis['Nipple to areola ratio'].quantile(0.9)

# Utworzenie fikcyjnych danych dla linii regresji w pełnym zakresie X
x_range = np.linspace(df_analysis['Areola a'].min(), df_analysis['Areola a'].max(), 100)

# Obliczenie przewidywanych wartości dla niskiego i wysokiego moderatora
# Przy założeniu, że model 4 to: win_ratio = b0 + b1*Areola_a + b2*Nipple_ratio + b3*Areola_a*Nipple_ratio
b0, b_areola_a, b_nipple_ratio, b_interaction = model_4.params.get('Intercept', 0), \
                                               model_4.params.get('Q("Areola a")', 0), \
                                               model_4.params.get('Q("Nipple to areola ratio")', 0), \
                                               model_4.params.get('Q("Areola a"):Q("Nipple to areola ratio")', 0)

y_low_mod = b0 + b_areola_a * x_range + b_nipple_ratio * low_mod + b_interaction * x_range * low_mod
y_high_mod = b0 + b_areola_a * x_range + b_nipple_ratio * high_mod + b_interaction * x_range * high_mod

# Rysowanie linii regresji
plt.plot(x_range, y_low_mod, color='green', linestyle='-', linewidth=2, label=f'Niski moderator (Q10: {low_mod:.2f})')
plt.plot(x_range, y_high_mod, color='red', linestyle='-', linewidth=2, label=f'Wysoki moderator (Q90: {high_mod:.2f})')


plt.title('Moderacja Nipple to areola ratio na zależności Win Ratio od Areola a')
plt.xlabel('Areola a')
plt.ylabel('Win Ratio')
plt.legend(title='Poziom moderatora', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()
