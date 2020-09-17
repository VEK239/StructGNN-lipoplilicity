from typing import List

import torch
from tqdm import tqdm

from chemprop.data import MoleculeDataLoader, MoleculeDataset, StandardScaler
from chemprop.models import MoleculeModel

from chemprop.args import TrainArgs


def predict(model: MoleculeModel,
            data_loader: MoleculeDataLoader,
            disable_progress_bar: bool = False,
            scaler: StandardScaler = None,
            args: TrainArgs = None) -> List[List[float]]:
    """
    Makes predictions on a dataset using an ensemble of models.

    :param model: A :class:`~chemprop.models.model.MoleculeModel`.
    :param data_loader: A :class:`~chemprop.data.data.MoleculeDataLoader`.
    :param disable_progress_bar: Whether to disable the progress bar.
    :param scaler: A :class:`~chemprop.features.scaler.StandardScaler` object fit on the training targets.
    :return: A list of lists of predictions. The outer list is molecules while the inner list is tasks.
    """
    model.eval()

    preds = []

    for batch in tqdm(data_loader, disable=disable_progress_bar):
        # Prepare batch
        batch: MoleculeDataset
        if args.additional_encoder:
            substructure_mol_batch = batch.batch_graph(model_type='substructures')
        mol_batch, features_batch = batch.batch_graph(), batch.features()

        # Make predictions
        with torch.no_grad():
            if args.additional_encoder:        
                batch_preds = model(mol_batch, substructure_mol_batch, features_batch)
            else:
                batch_preds = model(mol_batch, features_batch)

        batch_preds = batch_preds.data.cpu().numpy()

        # Inverse scale if regression
        if scaler is not None:
            batch_preds = scaler.inverse_transform(batch_preds)

        # Collect vectors
        batch_preds = batch_preds.tolist()
        preds.extend(batch_preds)

    return preds
