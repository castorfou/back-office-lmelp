---
status: accepted
---

# PGX est reconnue par sa clé d'hôte, jamais par son adresse

Joindre PGX par le VPN du NAS a cassé une hypothèse : « l'adresse dans `PGX_HOST` désigne
PGX ». Le VPN Server attribue les IP du pool `192.168.49.0/24` sans réservation, si bien qu'une
même adresse désigne PGX un jour et le laptop le lendemain ; PGX change aussi d'adresse à
chaque passage entre la maison d'été et les quartiers d'hiver. Avec
`StrictHostKeyChecking=accept-new` et un known_hosts indexé par IP, le backend acceptait la
première machine venue après un redémarrage (et lui aurait envoyé les audios), puis refusait
PGX elle-même quand l'adresse changeait de main, avec un message qui accusait
`authorized_keys`.

Nous identifions donc PGX par sa **clé d'hôte ED25519**, fournie dans `PGX_HOST_KEY`
(contenu de `/etc/ssh/ssh_host_ed25519_key.pub` lu sur PGX même), **obligatoire** au même
titre que les autres `PGX_*`. Toutes les commandes ssh/scp vérifient cette clé sous un alias
fixe (`HostKeyAlias=pgx`, `StrictHostKeyChecking=yes`) : une machine qui présente une autre
clé est refusée, y compris juste après un redémarrage. L'**adresse de PGX** devient une donnée
découverte : dernière adresse où elle a été trouvée (en mémoire), puis `PGX_HOST`, puis
balayage borné des plages de `PGX_HOST_CANDIDATES` (port 22, puis `ssh-keyscan` comparé à la
clé attendue).

## Considered Options

- **Garder `accept-new` quand `PGX_HOST_KEY` est absente** (repli avec avertissement) :
  écarté, c'est exactement la faille du premier contact ; il n'y a qu'un déploiement, la
  variable se renseigne une fois.
- **Effacer l'entrée périmée du known_hosts et réessayer** : écarté, on accepterait
  n'importe quelle machine qui récupère l'adresse, laptop compris.
- **IP VPN fixe pour PGX côté NAS** (`client-config-dir` / `ifconfig-push`) : écarté,
  l'interface de VPN Server ne le permet pas ; une modification manuelle de la configuration
  OpenVPN du NAS peut être écrasée par une mise à jour de DSM, et ne règle pas le changement
  de réseau entre les saisons.
- **TOFU persistant** (mémoriser la première clé vue, puis l'imposer) : écarté, le premier
  contact reste aveugle, et l'état persistant peut devenir faux sans que rien ne le signale.
