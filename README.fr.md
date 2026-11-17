# rbxexport

Addon Blender qui **vérifie tes modèles 3D et les exporte vers Roblox Studio** avec les bons réglages FBX, en deux clics.

Fini le modèle 100 fois trop grand, le mesh refusé par Roblox, ou l'échelle oubliée.

- **Check** trouve les problèmes avant Studio : plus de 20 000 triangles (comptés *après* modificateurs), échelle non appliquée ou négative, pas de UV, plusieurs matériaux, emplacements de matériau vides.
- **Export** écrit des FBX avec les réglages recommandés par Roblox : *FBX Unit Scale*, pas de leaf bones, textures copiées et intégrées, animation désactivée sauf demande.
- Un FBX **par objet** (nommé comme l'objet) ou un seul fichier pour toute la sélection.
- S'arrête s'il y a des erreurs (on peut forcer) et remet ta sélection comme avant.

Blender 4.2 ou plus. Licence MIT.

## Installer

1. Télécharge [`downloads/roblox_export-0.1.0.zip`](downloads/roblox_export-0.1.0.zip) (ne le décompresse pas).
2. Dans Blender : **Édition > Préférences > Obtenir des extensions**, petit menu en haut à droite, **Installer depuis le disque...**, choisis le zip. (Tu peux aussi glisser le zip dans la fenêtre Blender.)
3. Dans la vue 3D, appuie sur **N** : un onglet **Roblox** apparaît.

## Utiliser

1. Sélectionne tes meshes (ou choisis *Visible* pour prendre tous les meshes visibles).
2. Choisis le dossier de sortie. `//roblox_export/` = un dossier à côté du fichier `.blend`.
3. Clique **Check** pour lire les problèmes, puis **Export**.
4. Dans Studio : **Accueil > Importer 3D** et choisis les FBX.

Le menu **Fichier > Exporter > Roblox (.fbx)** fait la même chose avec les réglages du panneau.

Le détail des réglages et des contrôles est dans le [README anglais](README.md).

## Développer

```bash
python build.py                      # crée dist/roblox_export-<version>.zip
python -m pytest tests/test_core.py  # tests de la logique, Python normal
pip install bpy pytest && python -m pytest   # tous les tests, dans Blender
```

## Licence

MIT
