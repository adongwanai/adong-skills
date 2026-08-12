from __future__ import annotations

import copy
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from common import validate_profile
from career_ops import add_interview, add_job, add_offer, record_event, set_target, update_interview
from career_state import calculate_funnel, load_state, next_actions, save_state, validate_state, write_markdown
from import_materials import import_materials
from init_application import initialize_application
from init_workspace import initialize
from migrate_workspace import migrate
from render_application_resume import compile_application, render_application
from render_career_dashboard import render_dashboard
from render_portfolio import render_portfolio
from render_resumes import render_resumes
from validate_workspace import validate_workspace


def campus_profile() -> dict:
    return {
        "schema_version": 2,
        "sources": [
            {
                "id": "src-statement",
                "kind": "candidate_statement",
                "evidence_class": "statement",
                "value": "我用 LangChain 和 FAISS 做了一个课程 RAG 项目。",
                "accessed_at": "2026-08-12",
            }
        ],
        "candidate": {
            "name": "测试同学",
            "headline": "Agent 开发工程师",
            "career_stage": "campus",
            "location": "",
            "email": "",
            "phone": "",
            "links": [],
            "contact_visibility": {"resume": [], "public": []},
        },
        "education": [],
        "claims": [
            {
                "id": "project-rag",
                "category": "project",
                "status": "provided",
                "visibility": "resume",
                "public_safe": True,
                "ship_gate": "improve",
                "name": "课程知识库问答",
                "role": "个人项目",
                "start": "2026-03",
                "end": "2026-05",
                "source_refs": ["src-statement"],
                "contribution": "完成检索链路与问答接口",
                "limitation": "尚未建立固定评测集",
                "bullets": [
                    {
                        "id": "project-rag-b1",
                        "text": "使用 LangChain 与 FAISS 完成文档检索和带来源回答。",
                        "source_refs": ["src-statement"],
                    }
                ],
            }
        ],
        "resume_views": {
            "development": {
                "active": True,
                "headline": "Agent 开发工程师",
                "expected_pages": 1,
                "summary": "具备 Agent 应用开发与检索实践。",
                "summary_claim_ids": ["project-rag"],
                "claim_ids": ["project-rag"],
                "bullet_ids_by_claim": {"project-rag": ["project-rag-b1"]},
                "skills": [],
            },
            "algorithm": {
                "active": False,
                "headline": "Agent 算法工程师",
                "expected_pages": 1,
                "summary": "",
                "summary_claim_ids": [],
                "claim_ids": [],
                "bullet_ids_by_claim": {},
                "skills": [],
            },
        },
        "portfolio": {
            "label": "Agent 作品集",
            "summary": "",
            "summary_claim_ids": [],
            "metrics": [],
            "featured_claim_ids": [],
            "visuals": [],
            "resume_downloads": ["development"],
        },
    }


class UXWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="agent-career-kit-test-")
        self.workspace = Path(self.temp.name) / "career"
        initialize(str(self.workspace))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_profile(self, profile: dict | None = None) -> dict:
        profile = profile or campus_profile()
        (self.workspace / "candidate-profile.json").write_text(
            json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return profile

    def test_new_workspace_has_a_successful_intake_stage_without_indexing_bank(self) -> None:
        self.assertEqual(validate_workspace(self.workspace, stage="intake"), [])
        self.assertEqual(validate_workspace(self.workspace, stage="intake", require_dashboard=True), [])
        self.assertTrue((self.workspace / "intake.md").is_file())
        self.assertTrue((self.workspace / "application-dashboard.md").is_file())
        self.assertTrue((self.workspace / "outputs/career-dashboard/index.html").is_file())
        self.assertFalse((self.workspace / "interview-bank").exists())

    def test_resume_render_explains_when_no_direction_is_active(self) -> None:
        profile = campus_profile()
        profile["resume_views"]["development"]["active"] = False
        profile["resume_views"]["development"]["claim_ids"] = []
        profile["resume_views"]["development"]["summary"] = ""
        profile["resume_views"]["development"]["summary_claim_ids"] = []
        profile["resume_views"]["development"]["bullet_ids_by_claim"] = {}
        profile["portfolio"]["resume_downloads"] = []
        self.write_profile(profile)
        self.assertEqual(validate_profile(profile, self.workspace), [])
        with self.assertRaisesRegex(ValueError, "当前没有启用简历方向"):
            render_resumes(self.workspace)

    def test_campus_project_without_benchmark_can_render_one_direction(self) -> None:
        profile = self.write_profile()
        self.assertEqual(validate_profile(profile, self.workspace), [])
        outputs = render_resumes(self.workspace)
        self.assertEqual([path.parent.name for path in outputs], ["development"])
        tex = outputs[0].read_text(encoding="utf-8")
        self.assertIn(r"\zihao{5}\bfseries Agent 开发工程师", tex)
        self.assertIn(r"\section{项目经历}", tex)
        self.assertIn(r"\ResumeContacts{}", tex)
        self.assertFalse((self.workspace / "outputs" / "resumes" / "algorithm" / "main.tex").exists())
        tectonic = shutil.which("tectonic")
        if not tectonic:
            bundled = sorted((Path.home() / ".codex/plugins/cache/openai-bundled/latex").glob("*/bin/tectonic"))
            tectonic = str(bundled[-1]) if bundled else ""
        if tectonic and Path(tectonic).is_file():
            subprocess.run(
                [tectonic, "-X", "compile", "--outdir", str(outputs[0].parent), "--outfmt", "pdf", "main.tex"],
                cwd=outputs[0].parent,
                check=True,
                capture_output=True,
                text=True,
            )

    def test_pass_project_requires_stronger_evidence(self) -> None:
        profile = campus_profile()
        profile["claims"][0]["ship_gate"] = "pass"
        errors = validate_profile(profile, self.workspace)
        self.assertTrue(any("pass requires at least one artifact-class" in error for error in errors))

    def test_senior_project_with_artifacts_can_pass(self) -> None:
        profile = campus_profile()
        profile["candidate"]["career_stage"] = "senior"
        artifact = self.workspace / "source-materials" / "benchmark.md"
        artifact.write_text("# 固定任务集、基线、trace、失败分类与结果\n", encoding="utf-8")
        profile["sources"].append(
            {
                "id": "src-benchmark",
                "kind": "file",
                "evidence_class": "benchmark",
                "value": "source-materials/benchmark.md",
                "accessed_at": "2026-08-12",
            }
        )
        claim = profile["claims"][0]
        claim["ship_gate"] = "pass"
        claim["proof"] = {
            key: "project-rag-b1"
            for key in ("task_set", "baseline", "verification", "trace", "failure", "result")
        }
        claim["proof_refs"] = {
            key: ["src-statement", "src-benchmark"]
            for key in ("task_set", "baseline", "verification", "trace", "failure", "result")
        }
        claim["proof_notes"] = {
            "task_set": "固定 40 个代表性文档问答任务。",
            "baseline": "与无检索的直接回答基线比较。",
            "verification": "使用答案命中与引用一致性检查。",
            "trace": "保存检索、排序和生成三阶段 trace。",
            "failure": "区分未召回、错排和生成偏离三类失败。",
            "result": "记录同预算下的最终任务成功结果。",
        }
        self.assertEqual(validate_profile(profile, self.workspace), [])

    def test_portfolio_links_only_configured_resume(self) -> None:
        self.write_profile()
        render_resumes(self.workspace)
        index = render_portfolio(self.workspace).read_text(encoding="utf-8")
        self.assertIn("../resumes/development/main.pdf", index)
        self.assertNotIn("../resumes/algorithm/main.pdf", index)

    def test_application_packet_requires_approval_for_final_snapshot(self) -> None:
        self.write_profile()
        jd = self.workspace / "jd-bank" / "example.md"
        jd.write_text("# Agent 开发工程师\n\n要求具备 RAG 项目经验。\n", encoding="utf-8")
        output_dir = initialize_application(
            self.workspace, jd, "example-agent", "示例公司", "Agent 开发工程师", "development"
        )
        request_path = output_dir / "application-request.json"
        draft = render_application(self.workspace, request_path, final=False)
        self.assertTrue(draft.is_file())
        with self.assertRaisesRegex(ValueError, "必须先由用户确认"):
            render_application(self.workspace, request_path, final=True)

        request = json.loads(request_path.read_text(encoding="utf-8"))
        request["requirements"][0].update({"claim_ids": ["project-rag"], "gap": ""})
        request["jd_summary"] = "岗位负责 Agent 应用开发，要求具备 RAG 项目经验。"
        request["selection_rationale"] = "开发母版与 JD 方向一致，保留 RAG 项目作为首要证据。"
        request["risks"] = ["当前缺少固定评测集，需要在面试中如实说明。"]
        request["bullet_overrides"] = {
            "project-rag-b1": {
                "source_text": "使用 LangChain 与 FAISS 完成文档检索和带来源回答。",
                "text": "基于 LangChain 与 FAISS 实现文档检索和带来源回答，完成端到端问答链路。",
            }
        }
        request["approval"] = {
            "status": "approved",
            "approved_at": "2026-08-12",
            "record": "用户确认要求映射、选材和最终措辞。",
        }
        request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        final = render_application(self.workspace, request_path, final=True)
        self.assertTrue(final.is_file())
        expected_digest = hashlib.sha256(request_path.read_bytes()).hexdigest()
        final_text = final.read_text(encoding="utf-8")
        self.assertIn(expected_digest, final_text)
        self.assertIn("完成端到端问答链路", final_text)
        packet = (output_dir / "application-packet.md").read_text(encoding="utf-8")
        self.assertIn("已确认，可生成最终投递稿", packet)
        self.assertIn("岗位负责 Agent 应用开发", packet)
        self.assertNotIn("待填写", packet)
        self.assertNotIn("尚未确认", packet)
        pdf = compile_application(final)
        self.assertEqual(pdf.read_bytes()[:5], b"%PDF-")

    def test_failed_application_init_does_not_leave_a_dead_directory(self) -> None:
        self.write_profile()
        jd = self.workspace / "jd-bank" / "retry.md"
        jd.write_text("# Agent 开发工程师\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            initialize_application(self.workspace, jd, "retry-role", "示例公司", "算法岗", "algorithm")
        output_dir = self.workspace / "outputs" / "applications" / "retry-role"
        self.assertFalse(output_dir.exists())
        initialize_application(self.workspace, jd, "retry-role", "示例公司", "开发岗", "development")
        self.assertTrue((output_dir / "application-request.json").is_file())

    def test_legacy_csv_records_migrate_to_markdown(self) -> None:
        (self.workspace / "intake.md").unlink()
        (self.workspace / "application-dashboard.md").unlink()
        legacy = self.workspace / "outputs" / "application" / "application-tracker.csv"
        legacy.write_text(
            "application_id,company,role,source,route,status,date,next_action,notes\n"
            "app-01,示例公司,Agent 开发,内推,friend,interviewing,2026-08-12,准备系统设计,重点看可靠性\n",
            encoding="utf-8",
        )
        self.write_profile()
        changed = migrate(self.workspace, "campus")
        self.assertIn((self.workspace / "application-dashboard.md").resolve(), changed)
        dashboard = (self.workspace / "application-dashboard.md").read_text(encoding="utf-8")
        self.assertIn("示例公司", dashboard)
        self.assertIn("准备系统设计", dashboard)
        self.assertTrue(legacy.is_file())
        state = load_state(self.workspace)
        self.assertEqual(state["opportunities"][0]["company"], "示例公司")
        counts = tuple(len(state[key]) for key in ("opportunities", "events", "interviews", "offers"))
        migrate(self.workspace, "campus")
        migrated_again = load_state(self.workspace)
        self.assertEqual(
            tuple(len(migrated_again[key]) for key in ("opportunities", "events", "interviews", "offers")),
            counts,
        )

    def test_material_import_extracts_txt_and_docx_without_duplicates(self) -> None:
        resume = Path(self.temp.name) / "简历.txt"
        resume.write_text("测试同学\nAgent 开发工程师\n课程 RAG 项目", encoding="utf-8")
        docx = Path(self.temp.name) / "项目说明.docx"
        document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:r><w:t>实现工具调用与失败重试</w:t></w:r></w:p>
</w:body></w:document>"""
        with zipfile.ZipFile(docx, "w") as archive:
            archive.writestr("word/document.xml", document_xml)
        imported = import_materials(self.workspace, [resume, docx], "resume")
        self.assertEqual(len(imported), 2)
        self.assertIn("Agent 开发工程师", (self.workspace / imported[0]["extracted_path"]).read_text(encoding="utf-8"))
        self.assertIn("失败重试", (self.workspace / imported[1]["extracted_path"]).read_text(encoding="utf-8"))
        duplicate = import_materials(self.workspace, [resume], "resume")
        self.assertEqual(duplicate[0]["id"], imported[0]["id"])
        manifest = json.loads((self.workspace / "source-materials/materials.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["materials"]), 2)

    def test_parallel_material_imports_do_not_overwrite_manifest(self) -> None:
        resume = Path(self.temp.name) / "并发简历.txt"
        jd = Path(self.temp.name) / "并发岗位.txt"
        resume.write_text("校招生，目标 Agent 开发工程师。", encoding="utf-8")
        jd.write_text("Agent 开发岗位，要求 Python 与 RAG。", encoding="utf-8")
        script = SKILL_DIR / "scripts" / "import_materials.py"
        processes = [
            subprocess.Popen(
                [sys.executable, str(script), str(self.workspace), str(path), "--kind", kind],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for path, kind in ((resume, "resume"), (jd, "jd"))
        ]
        for process in processes:
            _, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, stderr)
        manifest = json.loads((self.workspace / "source-materials/materials.json").read_text(encoding="utf-8"))
        self.assertEqual({item["kind"] for item in manifest["materials"]}, {"resume", "jd"})
        self.assertEqual({item["original_name"] for item in manifest["materials"]}, {"并发简历.txt", "并发岗位.txt"})
        intake = (self.workspace / "intake.md").read_text(encoding="utf-8")
        self.assertIn("material-001", intake)
        self.assertIn("material-002", intake)

    def test_offer_funnel_prioritizes_offer_and_renders_dashboard(self) -> None:
        self.write_profile()
        state = load_state(self.workspace)
        set_target(
            state,
            argparse.Namespace(
                roles="Agent 开发工程师",
                locations="上海,杭州",
                minimum_offer="岗位方向匹配，薪资不低于当前总包",
                deadline="2026-09-30",
                notes="优先做可上线 Agent 系统的团队。",
            ),
        )
        add_job(
            state,
            argparse.Namespace(
                id="job-a",
                company="远山智能",
                role="Agent 开发工程师",
                source="内推",
                url="https://jobs.example.com/agent",
                location="上海",
                priority="high",
                fit="strong",
                fit_reasons="RAG 项目匹配,Python 工程能力",
                gaps="生产监控经验",
                status="researching",
                next_action="",
                next_action_date="",
                application_request="",
                date="2026-08-10",
                note="朋友推荐",
            ),
        )
        record_event(state, argparse.Namespace(job_id="job-a", type="applied", date="2026-08-11", note="官网投递"))
        record_event(state, argparse.Namespace(job_id="job-a", type="response", date="2026-08-12", note="约一面"))
        add_interview(
            state,
            argparse.Namespace(
                id="int-a1",
                job_id="job-a",
                round="技术一面",
                date="2026-08-14",
                status="scheduled",
                focus="RAG 评测与工具失败处理",
                result="",
                review_path="",
            ),
        )
        update_interview(
            state,
            argparse.Namespace(
                id="int-a1",
                round=None,
                date=None,
                status="passed",
                focus=None,
                result="通过，进入终面",
                review_path="outputs/interview/job-a-round1.md",
            ),
        )
        add_offer(
            state,
            argparse.Namespace(
                id="offer-a",
                job_id="job-a",
                level="P6",
                cash="45k x 15",
                equity="待确认",
                bonus="已含年终奖",
                conditions="三天内回复",
                deadline="2026-08-20",
                status="evaluating",
                risks="股权未写入书面 Offer",
                date="2026-08-16",
            ),
        )
        self.assertEqual(validate_state(state, self.workspace), [])
        save_state(self.workspace, state)
        markdown = write_markdown(self.workspace, state).read_text(encoding="utf-8")
        html = render_dashboard(self.workspace, state).read_text(encoding="utf-8")
        funnel = {item["key"]: item["count"] for item in calculate_funnel(state)}
        self.assertEqual(funnel, {"opportunities": 1, "applied": 1, "responses": 1, "interviews": 1, "offers": 1})
        self.assertEqual(next_actions(state)[0]["action"], "完成 Offer 比较与谈判决策")
        self.assertIn("远山智能", markdown)
        self.assertIn("完成 Offer 比较与谈判决策", html)
        self.assertIn("45k x 15", html)
        self.assertNotIn("—", html)

    def test_legacy_privacy_flags_do_not_block_resume_or_portfolio(self) -> None:
        profile = campus_profile()
        profile["candidate"].update(
            {
                "email": "candidate@example.com",
                "phone": "13800000000",
                "links": [{"label": "GitHub", "url": "https://github.com/example"}],
            }
        )
        profile["claims"][0].update({"visibility": "private", "public_safe": False})
        profile["portfolio"]["featured_claim_ids"] = ["project-rag"]
        self.write_profile(profile)
        self.assertEqual(validate_profile(profile, self.workspace), [])
        tex = render_resumes(self.workspace)[0].read_text(encoding="utf-8")
        portfolio = render_portfolio(self.workspace).read_text(encoding="utf-8")
        self.assertIn("candidate@example.com", tex)
        self.assertIn("课程知识库问答", portfolio)
        self.assertIn("candidate@example.com", portfolio)
        self.assertIn("https://github.com/example", portfolio)
        self.assertIn("13800000000", portfolio)


if __name__ == "__main__":
    unittest.main()
