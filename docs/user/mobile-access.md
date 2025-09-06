# Accès mobile à Back-office LMELP

Ce guide explique comment accéder à l'application Back-office LMELP depuis votre téléphone ou tablette sur le même réseau local.

## Prérequis

- Votre ordinateur et votre appareil mobile doivent être connectés au **même réseau Wi-Fi**
- L'application doit être démarrée en mode développement sur votre ordinateur
- Connaître l'adresse IP de votre ordinateur sur le réseau local

## Étapes d'accès

### 1. Démarrer l'application en mode développement

Sur votre ordinateur, démarrez l'application avec :

```bash
# Option 1: Script unifié (recommandé)
./scripts/start-dev.sh

# Option 2: Démarrage manuel
# Terminal 1 (backend)
ENVIRONMENT=development PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app

# Terminal 2 (frontend)
cd frontend && npm run dev
```

**Important**: Assurez-vous que la variable d'environnement `ENVIRONMENT=development` est définie pour activer l'accès réseau.

### 2. Trouver l'adresse IP de votre ordinateur

#### Sur Windows :
```cmd
ipconfig | findstr "IPv4"
```

#### Sur macOS/Linux :
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
# ou
ip addr show | grep "inet " | grep -v 127.0.0.1
```

Recherchez une adresse IP qui commence par :
- `192.168.x.x` (réseau domestique typique)
- `10.x.x.x` (réseau d'entreprise)
- `172.16.x.x` à `172.31.x.x` (réseau privé)

### 3. Accéder depuis votre téléphone

1. Ouvrez le navigateur web de votre téléphone
2. Saisissez l'URL : `http://[ADRESSE_IP]:5173`

**Exemple** : Si l'adresse IP de votre ordinateur est `192.168.1.100`, tapez :
```
http://192.168.1.100:5173
```

## Configuration automatique

L'application est configurée pour fonctionner automatiquement avec les appareils mobiles en mode développement :

### Backend (API)
- ✅ Écoute sur toutes les interfaces (`0.0.0.0:54321`)
- ✅ CORS configuré pour autoriser toutes les origines en développement
- ✅ Détection automatique du port disponible

### Frontend (Interface)
- ✅ Serveur Vite configuré avec `host: '0.0.0.0'`
- ✅ Proxy API configuré automatiquement
- ✅ Interface responsive adaptée aux écrans mobiles

## Résolution des problèmes courants

### ❌ "Cette page web n'est pas disponible"
**Causes possibles :**
- L'adresse IP est incorrecte
- L'application n'est pas démarrée
- Les appareils ne sont pas sur le même réseau

**Solutions :**
1. Vérifiez que l'application est démarrée et affiche les messages :
   ```
   🚀 Démarrage du serveur sur 0.0.0.0:54321
   Local:   http://localhost:5173/
   Network: http://192.168.x.x:5173/
   ```

2. Confirmez l'adresse IP avec `ipconfig` ou `ifconfig`
3. Assurez-vous que les deux appareils sont sur le même Wi-Fi

### ❌ Page se charge mais API ne fonctionne pas
**Cause :** Configuration CORS en production au lieu de développement

**Solution :** Démarrez avec la variable d'environnement :
```bash
ENVIRONMENT=development ./scripts/start-dev.sh
```

### ❌ Connexion lente ou instable
**Causes :** Réseau Wi-Fi surchargé ou signal faible

**Solutions :**
- Rapprochez-vous du routeur Wi-Fi
- Redémarrez votre routeur si nécessaire
- Utilisez la bande 5GHz si disponible

### ❌ Pare-feu bloque la connexion
**Solution :** Autorisez temporairement les connexions sur les ports 5173 et 54321

#### Windows Defender :
1. Panneau de configuration > Système et sécurité > Pare-feu Windows
2. Paramètres avancés > Règles de trafic entrant
3. Nouvelle règle > Port > TCP > Ports spécifiques : `5173,54321`

#### macOS :
```bash
sudo pfctl -d  # Désactive temporairement le pare-feu (redémarre automatiquement)
```

## Fonctionnalités mobiles

L'interface est optimisée pour mobile avec :

- 📱 **Design responsive** : S'adapte automatiquement à la taille d'écran
- 🎨 **Interface tactile** : Boutons et zones de clic adaptés au touch
- ⚡ **Performance optimisée** : Chargement rapide sur connexion mobile
- 🧭 **Navigation intuitive** : Menu de navigation adapté mobile

## Sécurité

⚠️ **Important pour la production** : Cette configuration permissive (`CORS: *`) est uniquement pour le développement. En production, l'accès est restreint aux domaines autorisés pour des raisons de sécurité.

---

Pour plus d'aide, consultez la [documentation développeur](../dev/) ou créez une issue sur le [dépôt GitHub](https://github.com/castorfou/back-office-lmelp/issues).
