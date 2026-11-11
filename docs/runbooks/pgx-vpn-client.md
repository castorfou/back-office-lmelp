# PGX — client VPN vers le NAS (quartiers d'hiver)

But : quand PGX n'est pas sur le réseau de la maison d'été, la connecter au serveur
OpenVPN du NAS pour que le backend lmelp (sur le NAS) la joigne en SSH et lui envoie les
épisodes à transcrire. Rien ne change dans lmelp à part la variable `PGX_HOST`.

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
# IP VPN de PGX : c'est elle qui ira dans PGX_HOST
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

1. Mettre l'IP `tun0` de PGX dans `PGX_HOST`, puis redémarrer le conteneur backend.
2. Test direct depuis le conteneur backend :
   ```bash
   sudo docker exec <conteneur-backend> bash -c 'timeout 3 bash -c "</dev/tcp/<ip-tun0-pgx>/22" && echo OK || echo KO'
   ```
3. Dans lmelp, page `/transcription-pgx` : la checklist doit être **entièrement verte**,
   puis lancer la transcription des épisodes en attente.

## 8. Au quotidien

- **Allumer PGX suffit** : le VPN monte tout seul, et le déclenchement automatique
  réessaie toutes les heures pendant 24h.
- **L'IP VPN n'est pas réservée** : si la checklist affiche « Machine joignable » en 🔴
  alors que PGX est allumée, comparer `ip -4 addr show tun0` avec `PGX_HOST` et corriger
  si besoin.

## 9. Retour à la maison d'été

Sur le réseau local, le VPN est inutile et peut gêner (routes vers `192.168.50.0/24` en
double) :

```bash
sudo systemctl disable --now openvpn-client@nas
```

Puis remettre l'IP locale de PGX dans `PGX_HOST` et redémarrer le conteneur backend. À
l'automne suivant : `sudo systemctl enable --now openvpn-client@nas`, puis les étapes 6
et 7.
