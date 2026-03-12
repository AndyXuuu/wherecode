from __future__ import annotations

from control_center.models import ActionExecuteResponse
from control_center.services.workflow_decompose_helpers_coverage import (
    build_synthetic_decomposition_fallback as build_synthetic_decomposition_fallback_impl,
    coverage_tag_default_module_map as coverage_tag_default_module_map_impl,
    coverage_tag_keyword_map as coverage_tag_keyword_map_impl,
    derive_required_coverage_tags as derive_required_coverage_tags_impl,
    extract_declared_coverage_tags as extract_declared_coverage_tags_impl,
    extract_modules_from_metadata as extract_modules_from_metadata_impl,
    extract_modules_from_summary as extract_modules_from_summary_impl,
    extract_requirement_module_map as extract_requirement_module_map_impl,
    infer_coverage_tags_from_module_key as infer_coverage_tags_from_module_key_impl,
    infer_coverage_tags_from_module_keys as infer_coverage_tags_from_module_keys_impl,
    infer_requirement_module_map_from_modules as infer_requirement_module_map_from_modules_impl,
    keyword_matches_haystack as keyword_matches_haystack_impl,
    normalize_module_candidates as normalize_module_candidates_impl,
    normalize_module_key as normalize_module_key_impl,
    validate_decomposition_coverage as validate_decomposition_coverage_impl,
    validate_requirement_module_mapping as validate_requirement_module_mapping_impl,
)
from control_center.services.workflow_decompose_helpers_tasks import (
    extract_module_task_packages as extract_module_task_packages_impl,
    infer_default_task_packages as infer_default_task_packages_impl,
    required_module_roles as required_module_roles_impl,
    validate_module_task_packages as validate_module_task_packages_impl,
)


class WorkflowDecomposeHelpersService:
    def build_chief_decompose_prompt(
        self,
        requirements: str,
        max_modules: int,
        module_hints: list[str],
        project_id: str,
        task_id: str | None,
    ) -> str:
        hints = ", ".join(item.strip() for item in module_hints if item.strip()) or "(none)"
        task_ref = task_id or "(none)"
        required_tags = self.derive_required_coverage_tags(
            requirements=requirements,
            module_hints=module_hints,
        )
        required_tags_text = ", ".join(required_tags) if required_tags else "(none)"
        return "\n".join(
            [
                "Role: chief-architect",
                "Context: software development project module decomposition for implementation planning.",
                "Task: decompose requirements into executable development modules for workflow bootstrap.",
                "Output requirements:",
                "- Return strict JSON for action-layer schema.",
                "- status must be success.",
                "- metadata.modules must be array of module keys.",
                "- metadata.decomposition.requirement_points must list key requirement bullets.",
                "- metadata.decomposition.modules should include module_key/responsibility/coverage_tags.",
                "- metadata.decomposition.coverage_check should include covered_tags/missing_tags.",
                "- metadata.decomposition.requirement_module_map must map required_coverage_tags to module keys.",
                "- requirement_module_map must cover every required_coverage_tag.",
                "- metadata.decomposition.module_task_packages must map module_key to task items.",
                "- each task item must include role and objective.",
                "- task item may include depends_on_roles for module-internal DAG scheduling.",
                "- task item may include deliverable and priority (1..5).",
                "- each module task package must cover roles: module-dev/doc-manager/qa-test/security-review.",
                f"- module count must be 1..{max_modules}.",
                "- module key format: lower-kebab-case; short and concrete.",
                "- modules must be directly mappable to implementation ownership.",
                "- summary should be one short sentence describing decomposition quality.",
                "- if required coverage cannot be satisfied, return status=failed with reason.",
                f"project_id={project_id}",
                f"task_id={task_ref}",
                f"module_hints={hints}",
                f"required_coverage_tags={required_tags_text}",
                "requirements:",
                requirements.strip(),
            ]
        )

    def extract_modules_from_chief_response(
        self,
        response: ActionExecuteResponse,
        max_modules: int,
    ) -> list[str]:
        metadata_modules = self.extract_modules_from_metadata(response.metadata)
        if metadata_modules:
            return metadata_modules[:max_modules]

        summary_modules = self.extract_modules_from_summary(response.summary)
        if summary_modules:
            return summary_modules[:max_modules]
        return []

    def extract_modules_from_metadata(self, metadata: dict[str, object]) -> list[str]:
        return extract_modules_from_metadata_impl(metadata)

    def extract_modules_from_summary(self, summary: str) -> list[str]:
        return extract_modules_from_summary_impl(summary)

    def normalize_module_candidates(self, values: list[object]) -> list[str]:
        return normalize_module_candidates_impl(values)

    def derive_required_coverage_tags(
        self,
        *,
        requirements: str,
        module_hints: list[str],
    ) -> list[str]:
        return derive_required_coverage_tags_impl(
            requirements=requirements,
            module_hints=module_hints,
        )

    def extract_declared_coverage_tags(self, metadata: dict[str, object]) -> set[str]:
        return extract_declared_coverage_tags_impl(metadata)

    def infer_coverage_tags_from_module_keys(self, module_keys: list[str]) -> set[str]:
        return infer_coverage_tags_from_module_keys_impl(module_keys)

    def infer_coverage_tags_from_module_key(self, module_key: str) -> set[str]:
        return infer_coverage_tags_from_module_key_impl(module_key)

    @staticmethod
    def coverage_tag_keyword_map() -> dict[str, tuple[str, ...]]:
        return coverage_tag_keyword_map_impl()

    @staticmethod
    def coverage_tag_default_module_map() -> dict[str, str]:
        return coverage_tag_default_module_map_impl()

    @staticmethod
    def normalize_module_key(value: str) -> str:
        return normalize_module_key_impl(value)

    def build_synthetic_decomposition_fallback(
        self,
        requirements: str,
        module_hints: list[str],
        max_modules: int,
    ) -> dict[str, object] | None:
        return build_synthetic_decomposition_fallback_impl(
            requirements,
            module_hints,
            max_modules,
            infer_default_task_packages_handler=self.infer_default_task_packages,
        )

    @staticmethod
    def keyword_matches_haystack(haystack: str, keyword: str) -> bool:
        return keyword_matches_haystack_impl(haystack, keyword)

    def validate_decomposition_coverage(
        self,
        requirements: str,
        module_hints: list[str],
        modules: list[str],
        chief_metadata: dict[str, object],
    ) -> tuple[list[str], list[str]]:
        return validate_decomposition_coverage_impl(
            requirements=requirements,
            module_hints=module_hints,
            modules=modules,
            chief_metadata=chief_metadata,
        )

    def validate_requirement_module_mapping(
        self,
        required_tags: list[str],
        modules: list[str],
        chief_metadata: dict[str, object],
    ) -> tuple[dict[str, list[str]], list[str], dict[str, list[str]], bool]:
        return validate_requirement_module_mapping_impl(
            required_tags=required_tags,
            modules=modules,
            chief_metadata=chief_metadata,
        )

    def extract_requirement_module_map(
        self,
        chief_metadata: dict[str, object],
    ) -> tuple[dict[str, list[str]], bool]:
        return extract_requirement_module_map_impl(chief_metadata)

    def infer_requirement_module_map_from_modules(
        self,
        modules: list[str],
    ) -> dict[str, list[str]]:
        return infer_requirement_module_map_from_modules_impl(modules)

    @staticmethod
    def required_module_roles() -> tuple[str, ...]:
        return required_module_roles_impl()

    def extract_module_task_packages(
        self,
        chief_metadata: dict[str, object],
    ) -> tuple[dict[str, list[dict[str, object]]], bool]:
        return extract_module_task_packages_impl(chief_metadata)

    def infer_default_task_packages(
        self,
        modules: list[str],
    ) -> dict[str, list[dict[str, str]]]:
        return infer_default_task_packages_impl(modules)

    def validate_module_task_packages(
        self,
        modules: list[str],
        chief_metadata: dict[str, object],
    ) -> tuple[
        dict[str, list[dict[str, object]]],
        list[str],
        dict[str, list[str]],
        dict[str, list[str]],
        bool,
    ]:
        return validate_module_task_packages_impl(modules, chief_metadata)

    @staticmethod
    def optional_text(value: object) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None
