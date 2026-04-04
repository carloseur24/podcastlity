import pytest
from pydantic import ValidationError

from scripts.models import (
    Session,
    Word,
    TranscriptSegment,
    Transcript,
    TranscriptRaw,
    SilenceInterval,
    SilenceMap,
    FillerWord,
    FillerMap,
    EnergyWindow,
    EnergyMap,
    Chapter,
    ChapterMap,
    KeepInterval,
    CutMap,
    BriefHook,
    BriefThumbnailConcept,
    BriefSceneOutline,
    Brief,
    Metadata,
)


class TestSession:
    def test_session_defaults(self):
        session = Session(session_id="test", topic="Test Topic")
        assert session.session_id == "test"
        assert session.topic == "Test Topic"
        assert session.profile == "default"
        assert session.status == "created"
        assert session.platform_targets == ["youtube_lf"]

    def test_session_valid_profile(self):
        session = Session(session_id="test", topic="Topic", profile="default")
        assert session.profile == "default"

    def test_session_invalid_profile(self):
        with pytest.raises(ValidationError):
            Session(session_id="test", topic="Topic", profile="invalid")

    def test_session_valid_status(self):
        session = Session(session_id="test", topic="Topic", status="ingested")
        assert session.status == "ingested"

    def test_session_invalid_status(self):
        with pytest.raises(ValidationError):
            Session(session_id="test", topic="Topic", status="invalid_status")

    def test_session_serialization(self):
        session = Session(session_id="test", topic="Topic")
        json_str = session.model_dump_json()
        assert '"session_id"' in json_str
        assert '"topic"' in json_str


class TestWord:
    def test_word_defaults(self):
        word = Word(word="hola", start=0.0, end=0.5, probability=0.9)
        assert word.word == "hola"
        assert word.start == 0.0
        assert word.end == 0.5
        assert word.probability == 0.9


class TestTranscriptSegment:
    def test_transcript_segment(self):
        segment = TranscriptSegment(
            id=1,
            start=0.0,
            end=5.0,
            text="Hola mundo",
            words=[
                Word(word="Hola", start=0.0, end=0.5, probability=0.9),
                Word(word="mundo", start=0.5, end=1.0, probability=0.9),
            ],
        )
        assert segment.id == 1
        assert len(segment.words) == 2


class TestTranscript:
    def test_transcript_defaults(self):
        t = Transcript()
        assert t.language == "es"
        assert t.duration == 0.0
        assert t.segments == []
        assert t.text == ""

    def test_transcript_with_segments(self):
        t = Transcript(
            duration=10.0,
            segments=[
                TranscriptSegment(id=1, start=0.0, end=5.0, text="First"),
                TranscriptSegment(id=2, start=5.0, end=10.0, text="Second"),
            ],
        )
        assert t.duration == 10.0
        assert len(t.segments) == 2


class TestSilenceInterval:
    def test_silence_interval(self):
        si = SilenceInterval(
            start=10.0, end=15.0, duration=5.0, type="between_sentences"
        )
        assert si.start == 10.0
        assert si.end == 15.0
        assert si.type == "between_sentences"


class TestSilenceMap:
    def test_silence_map_defaults(self):
        sm = SilenceMap()
        assert sm.total_silence_s == 0.0
        assert sm.silence_intervals == []
        assert sm.potential_time_saved_s == 0.0


class TestFillerWord:
    def test_filler_word(self):
        fw = FillerWord(word="eh", start=5.0, end=5.5, segment_id=1, confidence=0.8)
        assert fw.word == "eh"
        assert fw.confidence == 0.8


class TestFillerMap:
    def test_filler_map_defaults(self):
        fm = FillerMap()
        assert fm.total_fillers == 0
        assert fm.filler_rate_per_minute == 0.0
        assert fm.fillers == []


class TestEnergyWindow:
    def test_energy_window(self):
        ew = EnergyWindow(t=10.0, rms_norm=0.5, low_energy=False)
        assert ew.t == 10.0
        assert ew.rms_norm == 0.5


class TestEnergyMap:
    def test_energy_map_defaults(self):
        em = EnergyMap()
        assert em.windows == []
        assert em.low_energy_intervals == []


class TestChapter:
    def test_chapter(self):
        ch = Chapter(scene_id=1, start_s=0.0, title="Introduction")
        assert ch.scene_id == 1
        assert ch.title == "Introduction"


class TestChapterMap:
    def test_chapter_map_defaults(self):
        cm = ChapterMap()
        assert cm.chapters == []


class TestKeepInterval:
    def test_keep_interval_defaults(self):
        ki = KeepInterval(start=0.0, end=10.0)
        assert ki.start == 0.0
        assert ki.end == 10.0
        assert ki.type == "content"
        assert ki.scene_id is None

    def test_keep_interval_with_scene_id(self):
        ki = KeepInterval(start=0.0, end=10.0, scene_id=1, type="broll")
        assert ki.scene_id == 1
        assert ki.type == "broll"


class TestCutMap:
    def test_cut_map_defaults(self):
        cm = CutMap()
        assert cm.profile == "default"
        assert cm.total_input_duration_s == 0.0
        assert cm.total_output_duration_s == 0.0
        assert cm.keep_intervals == []
        assert cm.removed_silence_s == 0.0
        assert cm.removed_fillers == 0

    def test_cut_map_with_intervals(self):
        cm = CutMap(
            profile="default",
            keep_intervals=[
                KeepInterval(start=0.0, end=10.0),
                KeepInterval(start=15.0, end=25.0),
            ],
        )
        assert len(cm.keep_intervals) == 2


class TestBriefHook:
    def test_brief_hook(self):
        hook = BriefHook(text="Que pasaria si?", type="pregunta", energy="alta")
        assert hook.text == "Que pasaria si?"
        assert hook.type == "pregunta"
        assert hook.energy == "alta"


class TestBriefThumbnailConcept:
    def test_brief_thumbnail_concept(self):
        tc = BriefThumbnailConcept(
            texto_principal="GUIA COMPLETA",
            subtexto="2024",
            emocion="sorpresa",
            colores=["rojo", "amarillo"],
            composicion="center_text",
        )
        assert tc.texto_principal == "GUIA COMPLETA"


class TestBriefSceneOutline:
    def test_brief_scene_outline(self):
        scene = BriefSceneOutline(
            id=1, titulo="Intro", descripcion="Introduction scene", duracion_s=30
        )
        assert scene.id == 1
        assert scene.duracion_s == 30


class TestBrief:
    def test_brief_defaults(self):
        brief = Brief()
        assert brief.titles == []
        assert brief.hooks == []
        assert brief.thumbnail_concept is None
        assert brief.scene_outline == []
        assert brief.motion_style == "limpio"

    def test_brief_with_data(self):
        brief = Brief(
            titles=["Title 1"],
            hooks=[BriefHook(text="Hook 1", type="pregunta")],
            thumbnail_concept=BriefThumbnailConcept(
                texto_principal="Test",
                subtexto="Sub",
                emocion="feliz",
                colores=["azul"],
                composicion="test",
            ),
            scene_outline=[
                BriefSceneOutline(
                    id=1, titulo="Scene 1", descripcion="Desc", duracion_s=30
                )
            ],
            motion_style="energetico",
        )
        assert len(brief.titles) == 1
        assert len(brief.hooks) == 1
        assert brief.motion_style == "energetico"


class TestMetadata:
    def test_metadata_defaults(self):
        m = Metadata()
        assert m.titles == []
        assert m.hooks == []
        assert m.descriptions == {}
        assert m.tags == {}

    def test_metadata_with_data(self):
        m = Metadata(
            titles=["Title 1", "Title 2"],
            hooks=["Hook 1"],
            descriptions={"youtube": "Description for YT"},
            tags={"youtube": ["tag1", "tag2"]},
        )
        assert len(m.titles) == 2
        assert m.descriptions["youtube"] == "Description for YT"
        assert m.tags["youtube"] == ["tag1", "tag2"]


class TestModelIdempotency:
    def test_session_idempotent_serialization(self):
        s1 = Session(session_id="test", topic="Topic")
        json_str = s1.model_dump_json()
        s2 = Session.model_validate_json(json_str)
        assert s1.session_id == s2.session_id
        assert s1.topic == s2.topic

    def test_transcript_idempotent(self):
        t1 = Transcript(
            duration=10.0,
            segments=[TranscriptSegment(id=1, start=0.0, end=5.0, text="Test")],
        )
        json_str = t1.model_dump_json()
        t2 = Transcript.model_validate_json(json_str)
        assert t1.duration == t2.duration
        assert len(t1.segments) == len(t2.segments)
