{
  description = "epub2tts-edge — Conversor de EPUB a audiolibro con Microsoft Edge TTS";

  inputs = {
    # epub2tts-edge requiere Python < 3.12, nixos-23.11 trae Python 3.11
    nixpkgs.url     = "github:NixOS/nixpkgs/nixos-23.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # Python 3.11 con todas las dependencias de epub2tts-edge
        pythonEnv = pkgs.python311.withPackages (ps: [
          ps.pip
          ps.setuptools
          ps.wheel
          ps.nltk
          ps.beautifulsoup4
          ps.lxml
          ps.mutagen       # metadatos ID3/M4B
          ps.aiohttp       # edge-tts lo necesita
          ps.aiofiles
        ]);

      in {
        # ── nix develop ───────────────────────────────────────────────────────
        devShells.default = pkgs.mkShell {
          name = "epub2tts-edge";

          packages = [
            pythonEnv
            pkgs.ffmpeg
            pkgs.espeak-ng   # requerido por epub2tts-edge para tokenización
          ];

          shellHook = ''
            # Venv persistente para epub2tts-edge (pip --user no funciona en nix)
            VENV_DIR="$HOME/.local/share/epub2tts-edge-env"
            if [ ! -d "$VENV_DIR" ]; then
              echo "📦 Creando entorno virtual e instalando epub2tts-edge..."
              python3 -m venv "$VENV_DIR" --system-site-packages
              "$VENV_DIR/bin/pip" install git+https://github.com/aedocw/epub2tts-edge edge-tts --quiet
            fi
            source "$VENV_DIR/bin/activate"

            # Directorio para los datos de NLTK (tokenizador ~50MB)
            export NLTK_DATA="$HOME/.nltk_data"

            # Descargar tokenizador NLTK si no está
            python3 -c "
            import nltk, os
            nltk.download('punkt',        download_dir=os.environ['NLTK_DATA'], quiet=True)
            nltk.download('punkt_tab',    download_dir=os.environ['NLTK_DATA'], quiet=True)
            nltk.download('averaged_perceptron_tagger', download_dir=os.environ['NLTK_DATA'], quiet=True)
            " 2>/dev/null

            echo ""
            echo "  🎙️  epub2tts-edge listo"
            echo ""
            echo "  ── Uso básico ──────────────────────────────────────────"
            echo "  1) Extraer texto del EPUB:"
            echo "     epub2tts-edge libro.epub"
            echo ""
            echo "  2) Editar libro.txt (opcional):"
            echo "     - Primera línea:  Title: Título del libro"
            echo "     - Segunda línea:  Author: Nombre del autor"
            echo "     - Capítulos:      # Capítulo 1"
            echo "     - Eliminar índices, notas legales, etc."
            echo ""
            echo "  3) Generar audiolibro M4B:"
            echo "     epub2tts-edge libro.txt --cover libro.png --speaker es-ES-AlvaroNeural"
            echo ""
            echo "  ── Voces en español disponibles ────────────────────────"
            echo "     es-ES-AlvaroNeural      (hombre, España)"
            echo "     es-ES-ElviraNeural      (mujer, España)"
            echo "     es-MX-JorgeNeural       (hombre, México)"
            echo "     es-MX-DaliaNeural       (mujer, México)"
            echo "     es-AR-TomasNeural       (hombre, Argentina)"
            echo ""
            echo "  ── Listar todas las voces ──────────────────────────────"
            echo "     edge-tts --list-voices | grep es-"
            echo ""
          '';
        };
      });
}
