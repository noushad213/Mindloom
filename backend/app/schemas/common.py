from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StrictModel(ContractModel):
    model_config = ConfigDict(extra="forbid", strict=True)
