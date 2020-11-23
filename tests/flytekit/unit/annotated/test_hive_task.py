import pandas
import pytest

from flytekit.annotated import context_manager
from flytekit.annotated.base_task import kwtypes
from flytekit.annotated.context_manager import Image, ImageConfig
from flytekit.annotated.testing import task_mock
from flytekit.annotated.workflow import workflow
from flytekit.taskplugins.hive.task import HiveTask
from flytekit.types.schema import FlyteSchema


def test_serialization():
    my_schema = None

    hive_task = HiveTask(
        name="flytekit.demo.hive_task.hivequery1",
        inputs=kwtypes(my_schema=FlyteSchema, ds=str),
        cluster_label="flyte",
        query_template="""
            set engine=tez;
            insert overwrite directory '{{ .rawOutputDataPrefix }}' stored as parquet  -- will be unique per retry
            select *
            from blah
            where ds = '{{ .Inputs.ds }}' and uri = '{{ .inputs.my_schema }}'
        """,
        output_schema_type=my_schema,  # the schema literal's backend uri will be equal to the value of .raw_output_data
    )

    @workflow
    def my_wf(in_schema: FlyteSchema, ds: str) -> FlyteSchema:
        return hive_task(my_schema=in_schema, ds=ds)

    default_img = Image(name="default", fqn="test", tag="tag")
    registration_settings = context_manager.RegistrationSettings(
        project="proj",
        domain="dom",
        version="123",
        image_config=ImageConfig(default_image=default_img, images=[default_img]),
        env={},
        iam_role="test:iam:role",
        service_account=None,
    )
    with context_manager.FlyteContext.current_context().new_registration_settings(
        registration_settings=registration_settings
    ):
        sdk_task = hive_task.get_registerable_entity()
        assert "{{ .rawOutputDataPrefix" in sdk_task.custom["query"]["query"]
        assert "insert overwrite directory" in sdk_task.custom["query"]["query"]
        assert len(sdk_task.interface.inputs) == 2
        assert len(sdk_task.interface.outputs) == 1

        sdk_wf = my_wf.get_registerable_entity()
        assert sdk_wf.interface.outputs["out_0"].type.schema is not None
        assert sdk_wf.outputs[0].var == "out_0"
        assert sdk_wf.outputs[0].binding.promise.node_id == "node-0"
        assert sdk_wf.outputs[0].binding.promise.var == "results"


def test_local_exec():
    my_schema = None

    hive_task = HiveTask(
        name="flytekit.demo.hive_task.hivequery1",
        inputs={},
        cluster_label="flyte",
        query_template="""
            set engine=tez;
            insert overwrite directory '{{ .raw_output_data }}' stored as parquet  -- will be unique per retry
            select *
            from blah
            where ds = '{{ .Inputs.ds }}' and uri = '{{ .inputs.my_schema }}'
        """,
        output_schema_type=my_schema,  # the schema literal's backend uri will be equal to the value of .raw_output_data
    )

    assert len(hive_task.interface.inputs) == 0
    assert len(hive_task.interface.outputs) == 1

    # will not run locally
    with pytest.raises(Exception):
        hive_task()

    my_demo_output = pandas.DataFrame(data={"x": [1, 2], "y": ["3", "4"]})

    @workflow
    def my_wf() -> FlyteSchema:
        return hive_task()

    with task_mock(hive_task) as mock:
        mock.return_value = my_demo_output
        x = my_wf()
        df = x.open().all()
        y = df == my_demo_output
        assert y.all().all()