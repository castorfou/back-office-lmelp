# PGX — client VPN vers le NAS (quartiers d'hiver)

But : quand PGX n'est pas sur le réseau de la maison d'été, la connecter au serveur
OpenVPN du NAS pour que le backend lmelp (sur le NAS) la joigne en SSH et lui envoie les
épisodes à transcrire. lmelp retrouve PGX tout seul sur le VPN grâce à
`PGX_HOST_CANDIDATES` : aucune adresse à corriger à la main.

Repères réseau :

| Élément | Valeur |
|---|---|
| Réseau de la maison d'été | `192.168.50.0/24` |
| NAS | `192.168.50.207` |
| Réseau VPN (OpenVPN du NAS) | `192.168.49.0/24` |

Toutes les commandes se lancent **sur PGX**.

---

## 0. Prérequis

- Le **profil `.ovpn`** du VPN du NAS : le même que celui du laptop, ou un nouvel export
  depuis DSM → *VPN Server* → *OpenVPN* → *Exporter la configuration*. Dans un export
  Synology, la ligne `remote` contient parfois `YOUR_SERVER_IP` : la remplacer par
  l'adresse publique (DDNS) du NAS, comme dans le profil du laptop.
- Un **compte DSM autorisé à utiliser le VPN**. Conseillé : un compte dédié (par exemple
  `pgx-vpn`), qui n'a que le droit VPN. On peut le révoquer sans toucher au compte
  principal, et il évite que le laptop et PGX se disputent une session s'ils sont
  connectés en même temps.

## 1. Installer OpenVPN

```bash
sudo apt update
sudo apt install -y openvpn
```

## 2. Installer le profil

```bash
sudo install -m 600 ~/VPNConfig.ovpn /etc/openvpn/client/nas.conf   # adapter le chemin source
```

Ajouter les deux lignes propres à PGX :

```bash
sudo tee -a /etc/openvpn/client/nas.conf > /dev/null <<'EOF'

# --- PGX ---
# Split tunnel : seul le trafic vers les réseaux du NAS passe par le VPN
pull-filter ignore redirect-gateway
# Identifiants lus dans un fichier : connexion sans saisie au démarrage
auth-user-pass /etc/openvpn/client/nas.auth
EOF
```

Dans le profil, vérifier :

- qu'il n'y a **pas** de ligne `redirect-gateway` active (dans les exports Synology, elle
  est commentée : `#redirect-gateway def1`), sinon tout le trafic de PGX passerait par la
  maison d'été ;
- qu'il n'y a pas d'autre ligne `auth-user-pass` sans argument : la supprimer.

```bash
grep -nE '^[^#]*(redirect-gateway|auth-user-pass)' /etc/openvpn/client/nas.conf
# attendu : uniquement « pull-filter ignore redirect-gateway » et « auth-user-pass /etc/openvpn/client/nas.auth »
```

## 3. Fichier d'identifiants

Identifiant sur la ligne 1, mot de passe sur la ligne 2 :

```bash
sudo install -m 600 /dev/null /etc/openvpn/client/nas.auth
sudo nano /etc/openvpn/client/nas.auth
```

## 4. Tester au premier plan

```bash
sudo openvpn --config /etc/openvpn/client/nas.conf
```

Attendu : `Initialization Sequence Completed`. Dans un **autre terminal**, faire les
vérifications de l'étape 6, puis `Ctrl+C`.

Erreurs fréquentes :

- `AUTH_FAILED` : identifiants erronés, ou compte DSM sans permission VPN.
- La connexion ne s'établit pas : la ligne `remote` (adresse ou port) est fausse.

## 5. Activer au démarrage

```bash
sudo systemctl enable --now openvpn-client@nas
systemctl status openvpn-client@nas --no-pager
```

Le service redémarre avec PGX et se reconnecte tout seul après une coupure. Logs :
`journalctl -u openvpn-client@nas -f`.

## 6. Vérifications

```bash
# IP VPN de PGX : doit être dans une plage de PGX_HOST_CANDIDATES (192.168.49.0/24)
ip -4 addr show tun0

# Le NAS passe par le VPN...
ip route get 192.168.50.207      # attendu : « dev tun0 »
# ... mais pas Internet (split tunnel)
ip route get 1.1.1.1             # attendu : l'interface locale (wlan/eth), PAS tun0

# PGX joint le NAS
nc -zv 192.168.50.207 22
```

SSH doit être joignable depuis le VPN :

```bash
sudo ss -tlnp | grep ':22 '      # sshd écoute sur 0.0.0.0:22
sudo ufw status                  # si actif : sudo ufw allow from 192.168.49.0/24 to any port 22 proto tcp
```

Le service de transcription (conteneur whisper) doit tourner comme d'habitude :
`docker ps`.

## 7. Côté NAS

1. Récupérer la clé d'hôte de PGX, **sur PGX même** (pas par le réseau : c'est elle qui
   permettra de reconnaître PGX, il ne faut pas la demander à la machine qu'on cherche à
   vérifier) :
   ```bash
   cat /etc/ssh/ssh_host_ed25519_key.pub
   ```
   Copier la ligne entière dans `PGX_HOST_KEY` (`.env` du NAS). Elle ne change ni avec
   l'adresse ni avec le réseau : à faire une seule fois, ou après une réinstallation de PGX.
2. Vérifier que `PGX_HOST_CANDIDATES` contient le pool du VPN et le réseau local
   (`192.168.49.0/24,192.168.50.0/24`), puis redémarrer le conteneur backend. À faire une
   seule fois : `PGX_HOST` ne suit pas l'IP `tun0` de PGX.
3. Test direct depuis le conteneur backend :
   ```bash
   sudo docker exec <conteneur-backend> bash -c 'timeout 3 bash -c "</dev/tcp/<ip-tun0-pgx>/22" && echo OK || echo KO'
   ```
4. Dans lmelp, page `/transcription-pgx` : la checklist doit être **entièrement verte**.
   La ligne « PGX localisée » donne l'adresse où PGX a été trouvée. Lancer ensuite la
   transcription des épisodes en attente.

## 8. Au quotidien

- **Allumer PGX suffit** : le VPN monte tout seul, et le déclenchement automatique
  réessaie toutes les heures pendant 24h.
- **L'IP VPN n'est pas réservée** : lmelp cherche PGX dans `PGX_HOST_CANDIDATES` et ne
  retient que la machine qui présente `PGX_HOST_KEY`. Une autre cliente du VPN (le
  laptop, typiquement) qui récupère l'ancienne adresse de PGX est ignorée. Aucun
  `known_hosts` à nettoyer, `PGX_HOST` reste telle quelle.
- **« PGX localisée » en 🔴** (« Aucune machine avec l'identité de PGX parmi les
  candidats ») alors que PGX est allumée : vérifier que le VPN est monté
  (`ip -4 addr show tun0`) et que cette IP est bien dans une plage de
  `PGX_HOST_CANDIDATES`.
- Ne pas connecter le laptop au VPN du NAS en même temps que PGX limite ces échanges
  d'adresse.

## 9. Retour à la maison d'été

Sur le réseau local, le VPN est inutile et peut gêner (routes vers `192.168.50.0/24` en
double) :

```bash
sudo systemctl disable --now openvpn-client@nas
```

Côté NAS, la configuration reste la même : lmelp retrouve PGX sur le réseau local (`192.168.50.0/24`,
dans `PGX_HOST_CANDIDATES`). À l'automne suivant :
`sudo systemctl enable --now openvpn-client@nas`, puis l'étape 6.
