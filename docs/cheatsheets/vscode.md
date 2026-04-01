## multicurseur - modifier des variables
sur la variable `Ctrl-d` autant de fois que le nombre de variable à remplacer

## multicurseur - modifier des lignes sélectionnées
(pour inserer un > par ex en debut de ligne)

selection de ces lignes puis `Shift-Alt-i`

## cacher un repertoire du workspace (par exemple __pycache__)
ouvrir settings.json : `Ctrl-Shift-p` et taper Preferences: Open Settings (JSON) ⚙️
ajouter une entree dans __`files.exclude`__ ➕

```
    "files.exclude": {
        "**/.git": true,
        "**/__pycache__": true,
        "**/.ipynb_checkpoints": true
    },
```

## ctrl-c ctrl-v pour copier/coller dans le terminal
    Go to ‘Preferences > Keyboard Shortcuts’
    Set the ‘Terminal: Copy Selection’ keybindings to Ctrl-C
    Set the ‘Terminal: Paste into Active Terminal’ keybinding to Ctrl-V
