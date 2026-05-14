"""Agent per a la generació d'audiollibres mitjançant Venice TTS.

Converteix obres traduides (traduccio.md) en fitxers MP3 d'àudio,
amb suport per capítols, chunking intel·ligent i concatenació ffmpeg.
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

import yaml

from agents.base_agent import AgentConfig, BaseAgent
from agents.venice_client import VeniceClient, VeniceTTSError

# ══════════════════════════════════════════════════════════════════════════════
# Mapatge de veus per gènere (veus ElevenLabs verificades)
# ══════════════════════════════════════════════════════════════════════════════

VEUS_PER_GENERE: dict[str, str] = {
    "filosofia": "George",
    "narrativa": "Charlie",
    "poesia": "Charlotte",
    "teatre": "Adam",
    "oriental": "Laura",
    "assaig": "Daniel",
    "novel·la": "Charlie",
    "epopeia": "George",
}

# Màxim de caràcters per chunk (límit API: 4096, marge de seguretat)
MAX_CHARS_PER_CHUNK = 3800


class AgentNarrador(BaseAgent):
    """Agent per generar audiollibres a partir de traduccions.

    Llegeix traduccio.md, divideix en capítols/chunks, genera àudio TTS
    i concatena en MP3 complets usant ffmpeg.
    """

    agent_name: ClassVar[str] = "AgentNarrador"

    def __init__(
        self,
        config: AgentConfig | None = None,
        venice_client: VeniceClient | None = None,
    ) -> None:
        """Inicialitza l'agent narrador.

        Args:
            config: Configuració de l'agent base.
            venice_client: Client Venice. Si no es proporciona, es crea un.
        """
        super().__init__(config=config)
        self.venice = venice_client or VeniceClient()

    @property
    def system_prompt(self) -> str:
        """No s'utilitza per al narrador (no crida Claude)."""
        return "Agent narrador per audiollibres."

    # ══════════════════════════════════════════════════════════════════════════
    # Mètodes auxiliars
    # ══════════════════════════════════════════════════════════════════════════

    def _generar_audio_amb_retry(
        self, text: str, voice: str, max_retries: int = 3
    ) -> bytes:
        """Genera àudio amb retry i backoff exponencial per errors 500."""
        import time

        for attempt in range(1, max_retries + 1):
            try:
                audio = self.venice.generar_audio_sync(text=text, voice=voice)
                return audio
            except VeniceTTSError as e:
                if "500" in str(e) and attempt < max_retries:
                    wait = 5 * attempt
                    self.log_warning(
                        f"  ⚠️ Error 500, reintent {attempt}/{max_retries} "
                        f"(esperant {wait}s)... {e}"
                    )
                    time.sleep(wait)
                else:
                    raise

    # ══════════════════════════════════════════════════════════════════════════
    # Mètodes principals
    # ══════════════════════════════════════════════════════════════════════════

    def generar_audiollibre(
        self,
        obra_path: str | Path,
        voice: str | None = None,
        force: bool = False,
        nomes_capitols: bool = False,
        nomes_complet: bool = False,
    ) -> dict[str, Any]:
        """Genera l'audiollibre complet d'una obra.

        Args:
            obra_path: Camí al directori de l'obra.
            voice: Veu a utilitzar (sobreescriu el mapatge automàtic).
            force: Forçar regeneració encara que existeixi.
            nomes_capitols: Generar només els MP3 per capítol.
            nomes_complet: Generar només l'MP3 complet.

        Returns:
            Dict amb el manifest de l'audiollibre generat.

        Raises:
            FileNotFoundError: Si traduccio.md o metadata.yml no existeixen.
            VeniceTTSError: Si falla la generació TTS.
        """
        obra_path = Path(obra_path)
        self.log_info(f"Iniciant generació d'audiollibre: {obra_path}")

        # 1. Validacions
        self._validar_obra(obra_path, force)

        # 2. Llegir metadades i traducció
        metadata = self._llegir_metadata(obra_path)
        traduccio = self._llegir_traduccio(obra_path)

        # 3. Determinar veu
        if not voice:
            voice = self._obtenir_veu(metadata)

        self.log_info(f"Veu seleccionada: {voice}")

        # 4. Preparar directori de sortida
        audio_dir = obra_path / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        # 5. Separar en capítols
        capitol_data = self._separar_capitols(traduccio)
        te_capitols = len(capitol_data) > 1
        self.log_info(f"Capítols detectats: {len(capitol_data)}")

        # 6. Generar àudio
        total_chunks = sum(len(chunks) for _, chunks in capitol_data)
        resultats_capitols = []
        chunks_processats = 0
        mida_acumulada = 0
        start_time = time.time()

        for idx, (titol_capitol, chunks) in enumerate(capitol_data, 1):
            self.log_info(
                f"Capítol {idx}/{len(capitol_data)}: {titol_capitol} "
                f"({len(chunks)} chunks)"
            )

            # Generar àudio per cada chunk del capítol
            chunk_audio_files = []
            for chunk_idx, chunk_text in enumerate(chunks, 1):
                chunks_processats += 1
                pct = (chunks_processats / total_chunks) * 100
                self.log_info(
                    f"  Chunk {chunk_idx}/{len(chunks)} "
                    f"[{chunks_processats}/{total_chunks}] ({pct:.0f}%)"
                )

                try:
                    audio_bytes = self._generar_audio_amb_retry(
                        text=chunk_text,
                        voice=voice,
                        max_retries=3,
                    )

                    # Guardar chunk temporal
                    chunk_file = audio_dir / f"_chunk_{idx}_{chunk_idx}.mp3"
                    chunk_file.write_bytes(audio_bytes)
                    chunk_audio_files.append(chunk_file)
                    mida_acumulada += len(audio_bytes)

                    self.log_info(
                        f"  ✅ Chunk generat ({len(audio_bytes)} bytes)"
                    )

                except VeniceTTSError as e:
                    self.log_warning(f"  ❌ Error en chunk {chunk_idx}: {e}")
                    # Netejar fitxers temporals
                    for f in chunk_audio_files:
                        f.unlink(missing_ok=True)
                    raise

            # Concatenar chunks del capítol
            if len(chunk_audio_files) == 1:
                capitol_file = audio_dir / f"capitol_{idx:02d}.mp3"
                chunk_audio_files[0].rename(capitol_file)
            elif len(chunk_audio_files) > 1:
                capitol_file = audio_dir / f"capitol_{idx:02d}.mp3"
                self._concatenar_mp3(chunk_audio_files, capitol_file)
                # Netejar chunks temporals
                for f in chunk_audio_files:
                    f.unlink(missing_ok=True)
            else:
                continue

            capitol_size = capitol_file.stat().st_size
            capitol_duration = self._obtenir_durada_mp3(capitol_file)
            resultats_capitols.append({
                "fitxer": capitol_file.name,
                "titol": titol_capitol,
                "mida_bytes": capitol_size,
                "durada_segons": capitol_duration,
            })
            self.log_info(
                f"  📄 capitol_{idx:02d}.mp3 "
                f"({capitol_size / 1024:.1f} KB, {capitol_duration:.0f}s)"
            )

        # 7. Generar audiollibre complet (si escau)
        complet_file = None
        complet_duration = 0
        complet_size = 0

        if not nomes_capitols:
            if te_capitols and not nomes_complet:
                # Concatenar tots els capítols
                capitol_files = [audio_dir / r["fitxer"] for r in resultats_capitols]
                complet_file = audio_dir / "audiollibre_complet.mp3"
                self._concatenar_mp3(capitol_files, complet_file)
                complet_size = complet_file.stat().st_size
                complet_duration = self._obtenir_durada_mp3(complet_file)
                self.log_info(
                    f"🎵 audiollibre_complet.mp3 "
                    f"({complet_size / 1024:.1f} KB, {complet_duration:.0f}s)"
                )
            elif not te_capitols:
                # Un sol capítol → renombrar a complet
                if resultats_capitols:
                    src = audio_dir / resultats_capitols[0]["fitxer"]
                    complet_file = audio_dir / "audiollibre_complet.mp3"
                    src.rename(complet_file)
                    complet_size = complet_file.stat().st_size
                    complet_duration = self._obtenir_durada_mp3(complet_file)
                    resultats_capitols[0]["fitxer"] = "audiollibre_complet.mp3"
                    self.log_info(
                        f"🎵 audiollibre_complet.mp3 "
                        f"({complet_size / 1024:.1f} KB, {complet_duration:.0f}s)"
                    )

        # 8. Generar manifest
        elapsed = time.time() - start_time
        manifest = self._generar_manifest(
            metadata=metadata,
            voice=voice,
            capitols=resultats_capitols,
            complet_file=complet_file,
            complet_duration=complet_duration,
            complet_size=complet_size,
            elapsed=elapsed,
            total_chunks=total_chunks,
        )

        manifest_path = audio_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.log_info(f"📋 Manifest guardat: {manifest_path}")

        # 9. Actualitzar metadata.yml
        self._actualitzar_metadata_audiobook(
            obra_path,
            voice=voice,
            duration=complet_duration,
            size_mb=complet_size / (1024 * 1024),
        )
        self.log_info("✅ Audiollibre generat correctament!")

        return manifest

    # ══════════════════════════════════════════════════════════════════════════
    # Mètodes auxiliars
    # ══════════════════════════════════════════════════════════════════════════

    def _validar_obra(self, obra_path: Path, force: bool) -> None:
        """Valida que l'obra es pot processar.

        Args:
            obra_path: Camí al directori de l'obra.
            force: Si cal ignorar validació existent.

        Raises:
            FileNotFoundError: Si falten fitxers necessaris.
            FileExistsError: Si ja existeix audiollibre i no s'ha forçat.
        """
        if not (obra_path / "traduccio.md").exists():
            raise FileNotFoundError(
                f"No s'ha trobat traduccio.md a {obra_path}"
            )

        if not (obra_path / "metadata.yml").exists():
            raise FileNotFoundError(
                f"No s'ha trobat metadata.yml a {obra_path}"
            )

        # Verificar si ja existeix audiollibre
        audio_complet = obra_path / "audio" / "audiollibre_complet.mp3"
        if audio_complet.exists() and not force:
            raise FileExistsError(
                f"Ja existeix audiollibre a {audio_complet}. "
                f"Usa --force per regenerar."
            )

    def _llegir_metadata(self, obra_path: Path) -> dict[str, Any]:
        """Llegeix el fitxer metadata.yml.

        Args:
            obra_path: Camí al directori de l'obra.

        Returns:
            Dict amb les metadades de l'obra.
        """
        metadata_file = obra_path / "metadata.yml"
        with open(metadata_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _llegir_traduccio(self, obra_path: Path) -> str:
        """Llegeix el fitxer traduccio.md i neteja el text.

        Args:
            obra_path: Camí al directori de l'obra.

        Returns:
            Text net de la traducció.
        """
        traduccio_file = obra_path / "traduccio.md"
        with open(traduccio_file, "r", encoding="utf-8") as f:
            text = f.read()

        # Netejar: treure cabecera YAML (si n'hi ha), títol, autor, separadors
        lines = text.split("\n")
        clean_lines = []

        # Saltar capçaleres
        skip_header = True
        for line in lines:
            stripped = line.strip()

            # Saltar la primera línia si és el títol (# ...)
            if skip_header and stripped.startswith("# ") and not stripped.startswith("## "):
                skip_header = False
                continue

            # Saltar línia d'autor (*...*)
            if skip_header and stripped.startswith("*") and stripped.endswith("*"):
                continue

            # Saltar info de traducció
            if skip_header and "Traduït del" in stripped:
                skip_header = False
                continue

            # Saltar separadors horitzontals
            if stripped == "---":
                # Pot ser inici o final
                if clean_lines:
                    # És probablement un separador al mig, mantenir
                    # Però si és l'última secció (post-data), aturar
                    pass
                continue

            # Saltar nota final de traducció
            if "Traducció de domini públic" in stripped:
                break

            skip_header = False
            clean_lines.append(line)

        # Unir i netejar espais múltiples
        result = "\n".join(clean_lines)
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    def _obtenir_veu(self, metadata: dict[str, Any]) -> str:
        """Obté la veu adequada per a l'obra.

        Args:
            metadata: Metadades de l'obra.

        Returns:
            Nom de la veu ElevenLabs.
        """
        # 1. Comprovar audiobook_voice a metadata.yml
        obra_data = metadata.get("obra", {})
        if "audiobook_voice" in obra_data:
            return obra_data["audiobook_voice"]

        # 2. Mapatge per gènere
        genere = obra_data.get("genere", "") or obra_data.get("categoria", "")
        veu = VEUS_PER_GENERE.get(genere.lower())

        if veu:
            return veu

        # 3. Alternar codi de gènere curt (FIL, POE, etc.)
        genere_curt = metadata.get("genere", "")
        genere_map = {
            "FIL": "George", "POE": "Charlotte", "TEA": "Adam",
            "NOV": "Charlie", "SAG": "George", "ORI": "Laura", "EPO": "George",
        }
        veu = genere_map.get(genere_curt)
        if veu:
            return veu

        # 4. Per defecte: George (versàtil per textos clàssics)
        return "George"

    def _separar_capitols(
        self, text: str
    ) -> list[tuple[str, list[str]]]:
        """Separa el text en capítols i chunks.

        Detecta capítols per capçaleres ## (nivell 2).
        Si no n'hi ha, retorna un sol "capítol" amb el text sencer.

        Args:
            text: Text net de la traducció.

        Returns:
            Llista de tuples (títol_capítol, [chunks]).
        """
        # Detectar capítols per ## ...
        patro_capitol = re.compile(
            r"^(##\s+(.+?))$",
            re.MULTILINE,
        )

        coincidencies = list(patro_capitol.finditer(text))

        if len(coincidencies) < 2:
            # Un sol capítol o cap - chunking directe
            chunks = self._fer_chunking(text)
            titol = "Obra completa" if not coincidencies else coincidencies[0].group(2).strip()
            return [(titol, chunks)]

        # Separar per capítols
        capitol_data = []
        for i, match in enumerate(coincidencies):
            titol = match.group(2).strip()
            inici = match.end()

            if i + 1 < len(coincidencies):
                fi = coincidencies[i + 1].start()
            else:
                fi = len(text)

            contingut_capitol = text[inici:fi].strip()
            if contingut_capitol:
                chunks = self._fer_chunking(contingut_capitol)
                capitol_data.append((titol, chunks))

        return capitol_data if capitol_data else [("Obra completa", self._fer_chunking(text))]

    def _fer_chunking(self, text: str) -> list[str]:
        """Divideix el text en chunks respectant frases i paràgrafs.

        Mai talla pel mig d'una paraula. Màxim MAX_CHARS_PER_CHUNK caràcters.

        Args:
            text: Text a dividir.

        Returns:
            Llista de chunks de text.
        """
        if len(text) <= MAX_CHARS_PER_CHUNK:
            return [text] if text.strip() else []

        # Dividir per paràgrafs (separats per \n\n)
        paragrafs = re.split(r"\n\n+", text)
        paragrafs = [p.strip() for p in paragrafs if p.strip()]

        if not paragrafs:
            return [text]

        chunks = []
        chunk_actual = ""

        for paragraf in paragrafs:
            # Si un paràgraf sol és massa llarg, dividir per frases
            if len(paragraf) > MAX_CHARS_PER_CHUNK:
                # Primer afegir el chunk actual si existeix
                if chunk_actual:
                    chunks.append(chunk_actual.strip())
                    chunk_actual = ""

                # Dividir per frases (.) respetant màxim
                frases = re.split(r"(?<=[.!?])\s+", paragraf)
                frase_actual = ""

                for frase in frases:
                    if not frase.strip():
                        continue
                    if len(frase_actual) + len(frase) + 1 <= MAX_CHARS_PER_CHUNK:
                        frase_actual += (" " if frase_actual else "") + frase
                    else:
                        if frase_actual:
                            chunks.append(frase_actual.strip())
                        frase_actual = frase

                if frase_actual:
                    chunk_actual = frase_actual
                continue

            # Comprovar si el paràgraf cap al chunk actual
            if len(chunk_actual) + len(paragraf) + 2 <= MAX_CHARS_PER_CHUNK:
                chunk_actual += ("\n\n" if chunk_actual else "") + paragraf
            else:
                if chunk_actual:
                    chunks.append(chunk_actual.strip())
                chunk_actual = paragraf

        if chunk_actual:
            chunks.append(chunk_actual.strip())

        return chunks

    def _concatenar_mp3(
        self,
        input_files: list[Path],
        output_file: Path,
    ) -> None:
        """Concatena fitxers MP3 usant ffmpeg.

        Args:
            input_files: Llista de fitxers MP3 d'entrada.
            output_file: Fitxer MP3 de sortida.

        Raises:
            subprocess.CalledProcessError: Si ffmpeg falla.
        """
        if not input_files:
            raise ValueError("No hi ha fitxers per concatenar")

        if len(input_files) == 1:
            import shutil
            shutil.copy2(input_files[0], output_file)
            return

        # Crear fitxer de llista per ffmpeg
        list_file = output_file.parent / "_concat_list.txt"
        try:
            with open(list_file, "w", encoding="utf-8") as f:
                for inp in input_files:
                    # Escapar cometes simples al camí
                    escaped = str(inp).replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")

            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(list_file),
                    "-c", "copy",
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, "ffmpeg", result.stderr
                )

        finally:
            list_file.unlink(missing_ok=True)

    def _obtenir_durada_mp3(self, mp3_file: Path) -> float:
        """Obté la durada en segons d'un fitxer MP3.

        Args:
            mp3_file: Camí al fitxer MP3.

        Returns:
            Durada en segons (0 si no es pot determinar).
        """
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(mp3_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
            pass
        return 0.0

    def _generar_manifest(
        self,
        metadata: dict[str, Any],
        voice: str,
        capitols: list[dict],
        complet_file: Path | None,
        complet_duration: float,
        complet_size: int,
        elapsed: float,
        total_chunks: int,
    ) -> dict[str, Any]:
        """Genera el manifest JSON de l'audiollibre.

        Args:
            metadata: Metadades de l'obra.
            voice: Veu utilitzada.
            capitols: Llista de resultats per capítol.
            complet_file: Fitxer complet (si existeix).
            complet_duration: Durada total en segons.
            complet_size: Mida total en bytes.
            elapsed: Temps de generació en segons.
            total_chunks: Total de chunks processats.

        Returns:
            Dict amb el manifest complet.
        """
        obra = metadata.get("obra", {})
        # Estimació de cost: ~$0.30 per 1000 caràcters (turbo v2.5)
        total_chars = sum(len(c) for c in capitols)  # Aproximat
        total_chars_approx = total_chars * total_chunks  # Molt aproximat
        cost_estimat = (total_chars_approx / 1000) * 0.30

        manifest = {
            "obra": {
                "titol": obra.get("titol", "Desconegut"),
                "autor": obra.get("autor", "Desconegut"),
                "genere": obra.get("genere", ""),
            },
            "audiollibre": {
                "fitxer_complet": complet_file.name if complet_file else None,
                "durada_segons": complet_duration,
                "durada_format": self._formatar_durada(complet_duration),
                "mida_bytes": complet_size,
                "mida_mb": round(complet_size / (1024 * 1024), 2),
                "num_capitols": len(capitols),
                "total_chunks": total_chunks,
                "veu": voice,
                "model": self.venice.MODEL_TTS,
                "idioma": "ca",
            },
            "capitols": capitols,
            "generacio": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "durada_generacio_segons": round(elapsed, 1),
                "cost_estimat_usd": round(cost_estimat, 4),
            },
        }

        return manifest

    def _actualitzar_metadata_audiobook(
        self,
        obra_path: Path,
        voice: str,
        duration: float,
        size_mb: float,
    ) -> None:
        """Actualitza metadata.yml amb informació de l'audiollibre.

        Args:
            obra_path: Camí al directori de l'obra.
            voice: Veu utilitzada.
            duration: Durada en segons.
            size_mb: Mida en MB.
        """
        metadata_file = obra_path / "metadata.yml"
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = yaml.safe_load(f) or {}

        metadata["audiobook"] = {
            "generated": True,
            "voice": voice,
            "model": "tts-elevenlabs-turbo-v2-5",
            "duration_seconds": round(duration, 1),
            "size_mb": round(size_mb, 2),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        with open(metadata_file, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False)

    @staticmethod
    def _formatar_durada(segons: float) -> str:
        """Formata una durada en segons a format HH:MM:SS.

        Args:
            segons: Durada en segons.

        Returns:
            String formatat.
        """
        h = int(segons // 3600)
        m = int((segons % 3600) // 60)
        s = int(segons % 60)
        if h > 0:
            return f"{h}h {m:02d}m {s:02d}s"
        if m > 0:
            return f"{m}m {s:02d}s"
        return f"{s}s"

    def log_info(self, msg: str) -> None:
        """Log informatiu."""
        print(f"[Narrador] {msg}")

    def log_warning(self, msg: str) -> None:
        """Log d'advertència."""
        print(f"[Narrador ⚠️] {msg}")


if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("TEST AGENT NARRADOR")
    print("=" * 50)

    try:
        agent = AgentNarrador()
        print("✅ Agent creat")

        # Llistar veus
        veus = agent.venice.llistar_veus_tts_sync()
        print(f"✅ Veus disponibles: {veus}")

        # Prova de chunking
        test_text = "Això és un paràgraf de prova.\n\nAquest és un altre paràgraf més llarg que l'anterior, amb moltes paraules per provar que el chunking funcioni correctament sense tallar pel mig de paraules.\n\nUn últim paràgraf breu."
        chunks = agent._fer_chunking(test_text)
        print(f"✅ Chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks, 1):
            print(f"  Chunk {i}: {len(chunk)} chars")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
