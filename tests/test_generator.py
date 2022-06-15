#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2022 Pynguin Contributors
#
#  SPDX-License-Identifier: LGPL-3.0-or-later
#
import importlib
import threading
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

import pytest

import pynguin.analyses.typesystem as types
import pynguin.configuration as config
import pynguin.ga.postprocess as pp
import pynguin.generator as gen
from pynguin.instrumentation.machinery import install_import_hook
from pynguin.testcase.execution import ExecutionTracer, TestCaseExecutor


def test_init_with_configuration():
    conf = MagicMock(log_file=None)
    gen.set_configuration(configuration=conf)
    assert config.configuration == conf


def test__load_sut_failed():
    gen.set_configuration(
        configuration=MagicMock(log_file=None, module_name="this.does.not.exist")
    )
    assert gen._load_sut(MagicMock()) is False


def test__load_sut_success():
    gen.set_configuration(configuration=MagicMock(log_file=None))
    with mock.patch("importlib.import_module"):
        assert gen._load_sut(MagicMock())


def test_setup_test_cluster_empty():
    gen.set_configuration(
        configuration=MagicMock(
            type_inference=MagicMock(
                type_inference_strategy=config.TypeInferenceStrategy.TYPE_HINTS
            ),
        )
    )
    with mock.patch("pynguin.generator.generate_test_cluster") as gen_mock:
        tc = MagicMock()
        tc.num_accessible_objects_under_test.return_value = 0
        gen_mock.return_value = tc
        assert gen._setup_test_cluster() is None


def test_setup_test_cluster_not_empty():
    gen.set_configuration(
        configuration=MagicMock(
            type_inference=MagicMock(
                type_inference_strategy=config.TypeInferenceStrategy.TYPE_HINTS
            ),
        )
    )
    with mock.patch("pynguin.generator.generate_test_cluster") as gen_mock:
        tc = MagicMock()
        tc.num_accessible_objects_under_test.return_value = 1
        gen_mock.return_value = tc
        assert gen._setup_test_cluster()


@pytest.mark.parametrize(
    "conf_strategy, expected",
    [
        pytest.param(
            config.TypeInferenceStrategy.TYPE_HINTS,
            types.TypeInferenceStrategy.TYPE_HINTS,
        ),
        pytest.param(
            config.TypeInferenceStrategy.NONE,
            types.TypeInferenceStrategy.NONE,
        ),
        pytest.param(MagicMock(), types.TypeInferenceStrategy.TYPE_HINTS),
    ],
)
def test_setup_test_cluster_type_inference_strategy(conf_strategy, expected):
    gen.set_configuration(
        configuration=MagicMock(
            type_inference=MagicMock(type_inference_strategy=conf_strategy),
        )
    )
    with mock.patch("pynguin.generator.generate_test_cluster") as gen_mock:
        gen._setup_test_cluster()
        assert gen_mock.call_args.args[1] == expected


def test_setup_path_invalid_dir(tmp_path):
    gen.set_configuration(
        configuration=MagicMock(log_file=None, project_path=tmp_path / "nope")
    )
    assert gen._setup_path() is False


def test_setup_path_valid_dir(tmp_path):
    module_name = "test_module"
    gen.set_configuration(
        configuration=MagicMock(
            log_file=None, project_path=tmp_path, module_name=module_name
        )
    )
    with mock.patch("sys.path") as path_mock:
        assert gen._setup_path() is True
        path_mock.insert.assert_called_with(0, tmp_path)


def test_setup_hook():
    module_name = "test_module"
    gen.set_configuration(
        configuration=MagicMock(log_file=None, module_name=module_name)
    )
    with mock.patch.object(gen, "install_import_hook") as hook_mock:
        assert gen._setup_import_hook(None)
        hook_mock.assert_called_once()


def test__track_resulting_checked_coverage_exchanges_loader():
    config.configuration.statistics_output.coverage_metrics = [
        config.CoverageMetric.BRANCH,
    ]
    config.configuration.seeding.dynamic_constant_seeding = False
    tracer = ExecutionTracer()
    executor = TestCaseExecutor(tracer)
    result = MagicMock()

    tracer.current_thread_identifier = threading.current_thread().ident

    module_name = "tests.fixtures.linecoverage.plus"
    config.configuration.module_name = module_name
    with install_import_hook(module_name, tracer):
        module = importlib.import_module(module_name)
        importlib.reload(module)

        old_loader = module.__loader__

        gen._track_resulting_checked_coverage(executor, result, None)

        new_metrics = config.configuration.statistics_output.coverage_metrics
        assert len(new_metrics) == 1
        assert config.CoverageMetric.CHECKED in new_metrics

        assert old_loader is not module.__loader__


def test__reset_cache_for_result():
    test_case = MagicMock()
    result = MagicMock(test_case_chromosomes=[test_case])
    with mock.patch.object(test_case, "invalidate_cache") as test_case_cache_mock:
        with mock.patch.object(
            test_case, "remove_last_execution_result"
        ) as test_case_result_mock:
            with mock.patch.object(result, "invalidate_cache") as result_cache_mock:
                gen._reset_cache_for_result(result)
                result_cache_mock.assert_called_once()
                test_case_cache_mock.assert_called_once()
                test_case_result_mock.assert_called_once()


def test__minimize_assertions():
    config.configuration.test_case_output.assertion_generation = (
        config.AssertionGenerator.CHECKED_MINIMIZING_MUTATION
    )
    result = MagicMock()
    with mock.patch.object(result, "accept") as result_accept_mock:
        gen._minimize_assertions(result)
        result_accept_mock.assert_called_once()
        assert isinstance(
            result_accept_mock.call_args.args[0], pp.AssertionMinimization
        )


def test__setup_report_dir(tmp_path: Path):
    path = tmp_path / "foo" / "bar"
    config.configuration.statistics_output.report_dir = path.absolute()
    config.configuration.statistics_output.create_coverage_report = True
    assert gen._setup_report_dir()
    assert path.exists()
    assert path.is_dir()


def test__setup_report_dir_not_required(tmp_path: Path):
    path = tmp_path / "foo" / "bar"
    config.configuration.statistics_output.report_dir = path.absolute()
    config.configuration.statistics_output.create_coverage_report = False
    config.configuration.statistics_output.statistics_backend = (
        config.StatisticsBackend.NONE
    )
    assert gen._setup_report_dir()
    assert not path.exists()


def test_run(tmp_path):
    gen.set_configuration(
        configuration=MagicMock(log_file=None, project_path=tmp_path / "nope")
    )
    with mock.patch("pynguin.generator._run") as run_mock:
        gen.run_pynguin()
        run_mock.assert_called_once()


def test_integrate(tmp_path):
    project_path = Path(".").absolute()
    if project_path.name == "tests":
        project_path /= ".."  # pragma: no cover
    project_path = project_path / "docs" / "source" / "_static"
    configuration = config.Configuration(
        algorithm=config.Algorithm.MOSA,
        stopping=config.StoppingConfiguration(maximum_search_time=1),
        module_name="example",
        test_case_output=config.TestCaseOutputConfiguration(output_path=str(tmp_path)),
        project_path=str(project_path),
        statistics_output=config.StatisticsOutputConfiguration(
            report_dir=str(tmp_path), statistics_backend=config.StatisticsBackend.NONE
        ),
    )
    gen.set_configuration(configuration)
    result = gen.run_pynguin()
    assert result == gen.ReturnCode.OK
