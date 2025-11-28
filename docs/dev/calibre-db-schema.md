# Structure de la base de données Calibre (metadata.db)

Ce document décrit la structure de la base SQLite de Calibre (`metadata.db`) telle qu'utilisée dans back-office-lmelp.

## Vue d'ensemble

Calibre utilise une base SQLite avec une architecture normalisée :
- **Tables principales** : `books`, `authors`, `tags`, `publishers`, `series`, etc.
- **Tables de liaison** : `books_authors_link`, `books_tags_link`, etc.
- **Colonnes personnalisées** : Tables `custom_column_N` définies dans `custom_columns`

## Tables principales

### books

Table centrale contenant les livres.

```sql
CREATE TABLE books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    sort TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pubdate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    series_index REAL NOT NULL DEFAULT 1.0,
    author_sort TEXT,
    isbn TEXT DEFAULT "",
    lccn TEXT DEFAULT "",
    path TEXT NOT NULL DEFAULT "",
    flags INTEGER NOT NULL DEFAULT 1,
    uuid TEXT,
    has_cover BOOL DEFAULT 0,
    last_modified TIMESTAMP NOT NULL DEFAULT "2000-01-01 00:00:00+00:00"
);
```

**Champs importants** :
- `id` : Identifiant unique
- `title` : Titre du livre
- `isbn` : ISBN (peut être vide)
- `timestamp` : Date d'ajout dans Calibre
- `pubdate` : Date de publication
- `path` : Chemin relatif vers les fichiers du livre
- `has_cover` : Présence d'une couverture

### authors

Table des auteurs.

```sql
CREATE TABLE authors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE,
    sort TEXT COLLATE NOCASE,
    link TEXT NOT NULL DEFAULT ""
);
```

### tags

Table des tags/étiquettes.

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE
);
```

### publishers

Table des éditeurs.

```sql
CREATE TABLE publishers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE,
    sort TEXT COLLATE NOCASE
);
```

### series

Table des séries.

```sql
CREATE TABLE series (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE,
    sort TEXT COLLATE NOCASE
);
```

### identifiers

Table des identifiants externes (ISBN, etc.).

```sql
CREATE TABLE identifiers (
    id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL,
    type TEXT NOT NULL DEFAULT "isbn" COLLATE NOCASE,
    val TEXT NOT NULL COLLATE NOCASE,
    UNIQUE(book, type)
);
```

**IMPORTANT** : La plupart des ISBN sont dans cette table, **pas dans `books.isbn`**.

**Requête typique pour récupérer l'ISBN** :
```sql
SELECT i.val
FROM identifiers i
WHERE i.book = ? AND i.type = 'isbn'
LIMIT 1;
```

**Types courants** : `isbn`, `amazon`, `google`, `goodreads`, etc.

### ratings

Table des notes.

```sql
CREATE TABLE ratings (
    id INTEGER PRIMARY KEY,
    rating INTEGER CHECK(rating > -1 AND rating < 11)
);
```

**Important** : Les notes vont de 0 à 10 :
- `0` = Pas de note
- `2` = 1 étoile ⭐
- `4` = 2 étoiles ⭐⭐
- `6` = 3 étoiles ⭐⭐⭐
- `8` = 4 étoiles ⭐⭐⭐⭐
- `10` = 5 étoiles ⭐⭐⭐⭐⭐

### languages

Table des langues.

```sql
CREATE TABLE languages (
    id INTEGER PRIMARY KEY,
    lang_code TEXT NOT NULL COLLATE NOCASE
);
```

### comments

Table des commentaires/descriptions.

```sql
CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    book INTEGER NON NULL,
    text TEXT NOT NULL COLLATE NOCASE,
    UNIQUE(book)
);
```

## Tables de liaison (Many-to-Many)

### books_authors_link

Liaison livres ↔ auteurs (un livre peut avoir plusieurs auteurs).

```sql
CREATE TABLE books_authors_link (
    id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL,
    author INTEGER NOT NULL,
    UNIQUE(book, author)
);
```

**Requête typique** :
```sql
SELECT b.id, b.title, GROUP_CONCAT(a.name, ' & ') as authors
FROM books b
LEFT JOIN books_authors_link bal ON b.id = bal.book
LEFT JOIN authors a ON bal.author = a.id
GROUP BY b.id;
```

### books_tags_link

Liaison livres ↔ tags.

```sql
CREATE TABLE books_tags_link (
    id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL,
    tag INTEGER NOT NULL,
    UNIQUE(book, tag)
);
```

**Requête typique** :
```sql
SELECT b.id, b.title, GROUP_CONCAT(t.name, ', ') as tags
FROM books b
LEFT JOIN books_tags_link btl ON b.id = btl.book
LEFT JOIN tags t ON btl.tag = t.id
GROUP BY b.id;
```

### books_publishers_link

Liaison livres ↔ éditeurs (un livre = un éditeur).

```sql
CREATE TABLE books_publishers_link (
    id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL,
    publisher INTEGER NOT NULL,
    UNIQUE(book)
);
```

### books_series_link

Liaison livres ↔ séries.

```sql
CREATE TABLE books_series_link (
    id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL,
    series INTEGER NOT NULL,
    UNIQUE(book)
);
```

### books_ratings_link

Liaison livres ↔ notes.

```sql
CREATE TABLE books_ratings_link (
    id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    UNIQUE(book)
);
```

**Note** : `rating` ici est l'ID dans la table `ratings`, pas la note directe.

**Requête typique** :
```sql
SELECT b.id, b.title, r.rating
FROM books b
LEFT JOIN books_ratings_link brl ON b.id = brl.book
LEFT JOIN ratings r ON brl.rating = r.id;
```

### books_languages_link

Liaison livres ↔ langues.

```sql
CREATE TABLE books_languages_link (
    id INTEGER PRIMARY KEY,
    book INTEGER NOT NULL,
    lang_code INTEGER NOT NULL,
    item_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE(book, lang_code)
);
```

## Colonnes personnalisées

Les colonnes personnalisées sont définies dans la table `custom_columns` et stockées dans des tables `custom_column_N`.

### custom_columns

Métadonnées des colonnes personnalisées.

```sql
CREATE TABLE custom_columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    name TEXT NOT NULL,
    datatype TEXT NOT NULL,
    mark_for_delete BOOL DEFAULT 0 NOT NULL,
    editable BOOL DEFAULT 1 NOT NULL,
    display TEXT DEFAULT "{}" NOT NULL,
    is_multiple BOOL DEFAULT 0 NOT NULL,
    normalized BOOL NOT NULL
);
```

**Champs importants** :
- `label` : Nom technique **sans le préfixe `#`** (ex: `read`, `paper`, `text`)
- `name` : Nom affiché (ex: "Read", "paper", "Commentaire")
- `datatype` : Type de donnée (`bool`, `text`, `comments`, `datetime`, etc.)

**IMPORTANT** : Les labels sont stockés **sans le préfixe `#`** dans la base. Bien que Calibre affiche `#read` dans l'interface, le label en base est `read`.

**Exemple de requête** :
```sql
SELECT id, label, name, datatype FROM custom_columns;
```

Résultat (bibliothèque actuelle) :
```
id | label | name        | datatype
---+-------+-------------+----------
1  | paper | paper       | bool
2  | read  | Read        | bool
3  | text  | Commentaire | comments
```

Note : Les labels sont stockés **sans** le préfixe `#`.

### custom_column_N

Chaque colonne personnalisée a sa propre table `custom_column_N` (où N = id).

**Structure pour colonnes bool** :
```sql
CREATE TABLE custom_column_1 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book INTEGER NOT NULL,
    value BOOL NOT NULL,
    UNIQUE(book)
);
```

**Structure pour colonnes comments** :
```sql
CREATE TABLE custom_column_3 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book INTEGER NOT NULL,
    value TEXT NOT NULL COLLATE NOCASE,
    UNIQUE(book)
);
```

**Requête typique (colonne #read)** :
```sql
SELECT b.id, b.title, cc2.value as read_status
FROM books b
LEFT JOIN custom_column_2 cc2 ON b.id = cc2.book;
```

## Requêtes complètes recommandées

### Récupérer un livre avec toutes ses métadonnées

```sql
SELECT
    b.id,
    b.title,
    b.sort,
    b.isbn,
    b.timestamp,
    b.pubdate,
    b.last_modified,
    b.path,
    b.uuid,
    b.has_cover,
    b.series_index,

    -- Auteurs (concaténés)
    GROUP_CONCAT(DISTINCT a.name, ' & ') as authors,

    -- Tags (concaténés)
    GROUP_CONCAT(DISTINCT t.name, ', ') as tags,

    -- Éditeur (un seul)
    p.name as publisher,

    -- Série (une seule)
    s.name as series,

    -- Note (convertie)
    r.rating,

    -- Commentaires
    c.text as comments,

    -- Langues (concaténées)
    GROUP_CONCAT(DISTINCT l.lang_code, ', ') as languages,

    -- Colonnes personnalisées
    cc1.value as paper,
    cc2.value as read_status,
    cc3.value as personal_comments

FROM books b

-- Auteurs
LEFT JOIN books_authors_link bal ON b.id = bal.book
LEFT JOIN authors a ON bal.author = a.id

-- Tags
LEFT JOIN books_tags_link btl ON b.id = btl.book
LEFT JOIN tags t ON btl.tag = t.id

-- Éditeur
LEFT JOIN books_publishers_link bpl ON b.id = bpl.book
LEFT JOIN publishers p ON bpl.publisher = p.id

-- Série
LEFT JOIN books_series_link bsl ON b.id = bsl.book
LEFT JOIN series s ON bsl.series = s.id

-- Note
LEFT JOIN books_ratings_link brl ON b.id = brl.book
LEFT JOIN ratings r ON brl.rating = r.id

-- Commentaires
LEFT JOIN comments c ON b.id = c.book

-- Langues
LEFT JOIN books_languages_link bll ON b.id = bll.book
LEFT JOIN languages l ON bll.lang_code = l.id

-- Colonnes personnalisées (IDs spécifiques à votre base)
LEFT JOIN custom_column_1 cc1 ON b.id = cc1.book  -- #paper
LEFT JOIN custom_column_2 cc2 ON b.id = cc2.book  -- #read
LEFT JOIN custom_column_3 cc3 ON b.id = cc3.book  -- #text

WHERE b.id = ?
GROUP BY b.id;
```

### Lister les livres avec pagination

```sql
SELECT
    b.id,
    b.title,
    b.isbn,
    GROUP_CONCAT(DISTINCT a.name, ' & ') as authors,
    r.rating,
    cc2.value as read_status

FROM books b
LEFT JOIN books_authors_link bal ON b.id = bal.book
LEFT JOIN authors a ON bal.author = a.id
LEFT JOIN books_ratings_link brl ON b.id = brl.book
LEFT JOIN ratings r ON brl.rating = r.id
LEFT JOIN custom_column_2 cc2 ON b.id = cc2.book

GROUP BY b.id
ORDER BY b.timestamp DESC
LIMIT ? OFFSET ?;
```

### Filtrer par bibliothèque virtuelle (tag)

```sql
SELECT b.id, b.title, ...
FROM books b
-- Jointures...
WHERE EXISTS (
    SELECT 1 FROM books_tags_link btl
    JOIN tags t ON btl.tag = t.id
    WHERE btl.book = b.id AND t.name = 'guillaume'
)
GROUP BY b.id;
```

## Points d'attention

### 1. GROUP BY obligatoire

Toutes les requêtes avec `GROUP_CONCAT` nécessitent un `GROUP BY b.id` pour éviter les duplications.

### 2. Colonnes personnalisées dynamiques

Les IDs des colonnes personnalisées (`custom_column_N`) sont **spécifiques à chaque bibliothèque**. Il faut :
1. Interroger `custom_columns` pour trouver les IDs
2. Construire dynamiquement les jointures

### 3. Conversion notes

Les notes Calibre (0-10 par pas de 2) doivent être converties pour l'affichage :
- `rating / 2` = nombre d'étoiles (0-5)
- `rating = 0` = "Pas de note"

### 4. Performance

Pour de grandes bibliothèques (>1000 livres) :
- Utiliser `LIMIT` et `OFFSET` pour la pagination
- Créer des index sur les colonnes de recherche fréquente
- Éviter les `GROUP_CONCAT` sur de trop grandes listes

### 5. Lecture seule

**IMPORTANT** : Toujours ouvrir la connexion en mode lecture seule :
```python
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
```

Cela évite les problèmes de permissions et garantit qu'on ne modifie jamais la base Calibre.

## Ressources

- **Documentation Calibre DB** : https://manual.calibre-ebook.com/db_api.html
- **SQLite Docs** : https://www.sqlite.org/lang.html
- **Script exploration** : `scripts/explore_calibre.py`
- **Script comparaison** : `scripts/test_sqlite_vs_calibre_api.py`
