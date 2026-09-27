# Graph Report - wdapia  (2026-09-26)

## Corpus Check
- 71 files · ~59,051 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 3)

## Summary
- 207 nodes · 364 edges · 16 communities (11 shown, 5 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 55 edges (avg confidence: 0.85)
- Token cost: 134,608 input · 0 output

## Community Hubs (Navigation)
- Speckit Templates & Product Form
- Speckit Bash Scripts
- Django ORM & DRF Reference
- Produtos App Code & Imports
- Speckit SDD Pipeline Skills
- Listing & Model Tests
- Product Registration Tests
- Django Entry Points (WSGI/ASGI)
- TDD & Testing Strategy
- Doc-Sync Onboarding Agent
- Claude GitHub Workflows
- Produtos App Config
- Mandatory Doc Sync Rule
- Django Version Pin

## God Nodes (most connected - your core abstractions)
1. `Produto` - 20 edges
2. `CadastroProdutoTests` - 15 edges
3. `Tasks: Product Registry Home (T001-T018)` - 13 edges
4. `speckit-implement Skill` - 12 edges
5. `Implementation Plan: Product Registry Home` - 12 edges
6. `ListagemProdutoTests` - 11 edges
7. `home()` - 11 edges
8. `speckit-analyze Skill` - 11 edges
9. `speckit-specify Skill` - 11 edges
10. `create-new-feature.sh script` - 10 edges

## Surprising Connections (you probably didn't know these)
- `ModelForm with model-field validation (R3)` --rationale_for--> `ProdutoForm`  [INFERRED]
  specs/001-product-registry-home/research.md → produtos/forms.py
- `Newest-first ordering via criado_em index (R5)` --rationale_for--> `Produto`  [INFERRED]
  specs/001-product-registry-home/research.md → produtos/models.py
- `home()` --implements--> `User Story 1: Cadastrar um produto pela home`  [INFERRED]
  produtos/views.py → specs/001-product-registry-home/spec.md
- `home()` --implements--> `User Story 2: Ver os produtos cadastrados na mesma página`  [INFERRED]
  produtos/views.py → specs/001-product-registry-home/spec.md
- `Tasks: Product Registry Home (T001-T018)` --references--> `ProdutoForm`  [INFERRED]
  specs/001-product-registry-home/tasks.md → produtos/forms.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Spec-Driven Development pipeline (constitution -> specify -> clarify -> plan -> tasks -> analyze -> implement)** — _claude_skills_speckit_constitution_skill_speckit_constitution, _claude_skills_speckit_specify_skill_speckit_specify, _claude_skills_speckit_clarify_skill_speckit_clarify, _claude_skills_speckit_plan_skill_speckit_plan, _claude_skills_speckit_tasks_skill_speckit_tasks, _claude_skills_speckit_analyze_skill_speckit_analyze, _claude_skills_speckit_implement_skill_speckit_implement [EXTRACTED 1.00]
- **N+1 query mitigation techniques** — _agents_skills_django_expert_references_models_and_orm_n_plus_1_query_problem, _agents_skills_django_expert_references_models_and_orm_select_related, _agents_skills_django_expert_references_models_and_orm_prefetch_related, _agents_skills_django_expert_references_performance_optimization, _agents_skills_django_expert_references_examples [EXTRACTED 1.00]
- **Django testing toolkit (pytest-django, factories, mocking, coverage)** — _agents_skills_django_expert_references_testing_strategies_pytest_django, _agents_skills_django_tdd_skill_factory_boy, _agents_skills_django_tdd_skill_mocking, _agents_skills_django_tdd_skill_coverage, _agents_skills_django_expert_references_testing_strategies_fixtures_and_factories [INFERRED 0.85]
- **Spec-kit SDD artifact chain for feature 001** — specs_001_product_registry_home_spec_feature_spec, specs_001_product_registry_home_plan_implementation_plan, specs_001_product_registry_home_research_post_redirect_get, specs_001_product_registry_home_data_model_produto_entity, specs_001_product_registry_home_contracts_home_page_contract, specs_001_product_registry_home_tasks_task_list, _specify_workflows_speckit_workflow_speckit_workflow [EXTRACTED 1.00]
- **Home page register-and-list PRG flow** — produtos_views_home, produtos_forms_produtoform, produtos_models_produto, produtos_templates_produtos_home_home_template, specs_001_product_registry_home_research_post_redirect_get [INFERRED 0.85]

## Communities (16 total, 5 thin omitted)

### Community 0 - "Speckit Templates & Product Form"
Cohesion: 0.10
Nodes (36): Project Constitution (unfilled template), Checklist Template, Constitution Template, Implementation Plan Template, Feature Specification Template, Tasks Template, Full SDD Cycle Workflow (speckit), Project Conventions (apps at repo root, include() URLs, APP_DIRS templates) (+28 more)

### Community 1 - "Speckit Bash Scripts"
Cohesion: 0.13
Nodes (29): check-prerequisites.sh script, check_dir(), check_file(), find_specify_root(), format_speckit_command(), get_current_branch(), get_feature_paths(), get_invoke_separator() (+21 more)

### Community 2 - "Django ORM & DRF Reference"
Cohesion: 0.10
Nodes (30): DRF Guidelines Reference, DRF Permissions, ModelSerializer, ModelViewSet, DRF Throttling (Rate Limiting), Django Expert Examples, Models and ORM Reference, Bulk Operations (bulk_create/bulk_update/update) (+22 more)

### Community 3 - "Produtos App Code & Imports"
Cohesion: 0.13
Nodes (11): URL configuration for core project. The `urlpatterns` list routes URLs to…, django, django_contrib, django_core_validators, django_db, django_shortcuts, django_urls, django_views_decorators_http (+3 more)

### Community 4 - "Speckit SDD Pipeline Skills"
Cohesion: 0.40
Nodes (16): .specify/extensions.yml hooks, speckit-analyze Skill, checklists/ (requirements quality checklists), speckit-checklist Skill, speckit-clarify Skill, constitution.md (project principles), speckit-constitution Skill, speckit-converge Skill (+8 more)

### Community 5 - "Listing & Model Tests"
Cohesion: 0.13
Nodes (7): Mandatory TDD Workflow (django-tdd), django_test, ListagemProdutoTests, ProdutoModelTests, coverage 7.16.1, Django built-in test runner (R8), TestCase

### Community 7 - "Django Entry Points (WSGI/ASGI)"
Cohesion: 0.17
Nodes (9): ASGI config for core project. It exposes the ASGI callable as a module-level…, WSGI config for core project. It exposes the WSGI callable as a module-level…, django_core_asgi, django_core_wsgi, main(), Django's command-line utility for administrative tasks., Run administrative tasks., os (+1 more)

### Community 8 - "TDD & Testing Strategy"
Cohesion: 0.24
Nodes (10): Testing Strategies Reference, Fixtures and Factories, pytest-django, TestCase vs TransactionTestCase, Coverage Goals, Django TDD Skill, factory_boy Factories, Integration (Full Flow) Testing (+2 more)

### Community 9 - "Doc-Sync Onboarding Agent"
Cohesion: 0.67
Nodes (4): doc-sync-onboarding Agent, Documentation Map (CLAUDE.md, docs/index.md, architecture.md, database.md, admin.md, docs/apps/<name>.md), Hardcoded docs path /home/caio/pythonProjects/estudeflow/planeje/docs, Persistent Agent Memory (MEMORY.md index)

### Community 10 - "Claude GitHub Workflows"
Cohesion: 0.67
Nodes (4): Claude Code @claude Mention Workflow, Issue Triage Workflow (Claude), Structured Issue Triage Comment Format, anthropics/claude-code-action@v1

### Community 11 - "Produtos App Config"
Cohesion: 0.50
Nodes (3): AppConfig, django_apps, ProdutosConfig

## Ambiguous Edges - Review These
- `Documentation Map (CLAUDE.md, docs/index.md, architecture.md, database.md, admin.md, docs/apps/<name>.md)` → `Hardcoded docs path /home/caio/pythonProjects/estudeflow/planeje/docs`  [AMBIGUOUS]
  .claude/agents/doc-sync-onboarding.md · relation: conceptually_related_to

## Knowledge Gaps
- **24 isolated node(s):** `common.sh script`, `Meta`, `Migration`, `Meta`, `Bulk Operations (bulk_create/bulk_update/update)` (+19 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 58 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Documentation Map (CLAUDE.md, docs/index.md, architecture.md, database.md, admin.md, docs/apps/<name>.md)` and `Hardcoded docs path /home/caio/pythonProjects/estudeflow/planeje/docs`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `speckit-implement Skill` connect `Speckit SDD Pipeline Skills` to `TDD & Testing Strategy`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `Red-Green-Refactor Cycle` connect `TDD & Testing Strategy` to `Speckit SDD Pipeline Skills`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `Produto` (e.g. with `ProdutoForm` and `Home Page Template (produtos/home.html)`) actually correct?**
  _`Produto` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `Tasks: Product Registry Home (T001-T018)` (e.g. with `Tasks Template` and `settings.py`) actually correct?**
  _`Tasks: Product Registry Home (T001-T018)` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `common.sh script`, `Meta`, `Migration` to the rest of the system?**
  _24 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Speckit Templates & Product Form` be split into smaller, more focused modules?**
  _Cohesion score 0.0953058321479374 - nodes in this community are weakly interconnected._