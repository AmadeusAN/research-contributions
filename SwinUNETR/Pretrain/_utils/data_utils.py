# Copyright 2020 - 2022 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from monai.data import CacheDataset, DataLoader, Dataset, DistributedSampler, SmartCacheDataset, load_decathlon_datalist
from monai.transforms import (
    # AddChanneld,
    EnsureChannelFirstd,
    Compose,
    CropForegroundd,
    LoadImaged,
    NormalizeIntensityd,
    Orientationd,
    RandCropByPosNegLabeld,
    RandSpatialCropSamplesd,
    ScaleIntensityRanged,
    Spacingd,
    SpatialPadd,
    ToTensord,
)

from data import setup_data, setup_pretraining_data_SwinUNETR
from pathlib import Path
import json
from sklearn.model_selection import train_test_split


def get_loader(args):
    # splits1 = "/dataset_LUNA16_0.json"
    # splits2 = "/dataset_TCIAcovid19_0.json"
    # splits3 = "/dataset_HNSCC_0.json"
    # splits4 = "/dataset_TCIAcolon_v2_0.json"
    # splits5 = "/dataset_LIDC_0.json"
    # list_dir = "./jsons"
    # jsonlist1 = list_dir + splits1
    # jsonlist2 = list_dir + splits2
    # jsonlist3 = list_dir + splits3
    # jsonlist4 = list_dir + splits4
    # jsonlist5 = list_dir + splits5
    # datadir1 = "/dataset/dataset1"
    # datadir2 = "/dataset/dataset2"
    # datadir3 = "/dataset/dataset3"
    # datadir4 = "/dataset/dataset4"
    # datadir5 = "/dataset/dataset8"
    # num_workers = 4
    # datalist1 = load_decathlon_datalist(jsonlist1, False, "training", base_dir=datadir1)
    # print("Dataset 1 LUNA16: number of data: {}".format(len(datalist1)))
    # new_datalist1 = []
    # for item in datalist1:
    #     item_dict = {"image": item["image"]}
    #     new_datalist1.append(item_dict)
    # datalist2 = load_decathlon_datalist(jsonlist2, False, "training", base_dir=datadir2)
    # print("Dataset 2 Covid 19: number of data: {}".format(len(datalist2)))
    # datalist3 = load_decathlon_datalist(jsonlist3, False, "training", base_dir=datadir3)
    # print("Dataset 3 HNSCC: number of data: {}".format(len(datalist3)))
    # datalist4 = load_decathlon_datalist(jsonlist4, False, "training", base_dir=datadir4)
    # print("Dataset 4 TCIA Colon: number of data: {}".format(len(datalist4)))
    # datalist5 = load_decathlon_datalist(jsonlist5, False, "training", base_dir=datadir5)
    # print("Dataset 5: number of data: {}".format(len(datalist5)))
    # vallist1 = load_decathlon_datalist(jsonlist1, False, "validation", base_dir=datadir1)
    # vallist2 = load_decathlon_datalist(jsonlist2, False, "validation", base_dir=datadir2)
    # vallist3 = load_decathlon_datalist(jsonlist3, False, "validation", base_dir=datadir3)
    # vallist4 = load_decathlon_datalist(jsonlist4, False, "validation", base_dir=datadir4)
    # vallist5 = load_decathlon_datalist(jsonlist5, False, "validation", base_dir=datadir5)
    # datalist = new_datalist1 + datalist2 + datalist3 + datalist4 + datalist5
    # val_files = vallist1 + vallist2 + vallist3 + vallist4 + vallist5

    base_dir = "/public1/cjh/workspace/AbdominalSegmentation/dataset/raw_dataset"
    manifest1 = f"{base_dir}/abdomenct1k/manifest.json"
    manifest2 = f"{base_dir}/LITS/media/nas/01_Datasets/CT/LITS/manifest.json"
    manifest3 = f"{base_dir}/RAOS/RAOS-Real/CancerImages(Set1)/manifest.json"
    manifest4 = f"{base_dir}/MM-WHS/MM-WHS 2017 Dataset/manifest.json"
    # manifest5 = f"{base_dir}/MSD/manifest.json"
    manifest6 = f"{base_dir}/LUNA16/manifest.json"

    manifest_list = [manifest1, manifest2, manifest3, manifest4, manifest6]
    datalist = []
    val_files = []
    for manifest in manifest_list:
        with Path(manifest).open("r") as f:
            json_f = json.load(f)
        json_training = json_f["training"]
        # 检验一下图像是否是单通道
        test_image = json_training[0]
        test_image = LoadImaged(keys=["image"])(test_image)["image"]
        if len(test_image.shape) != 3:
            raise ValueError("The image is not single channel")

        json_val = json_f.get("validation", None)
        if json_val is None and json_f.get("testing", None) is None:
            # 该数据集仅包含训练数据集，因此需要切分
            josn_training, json_val = train_test_split(json_training, test_size=0.2, random_state=42)
        else:
            json_val = json_f["testing"]
        datalist += [{"image": item["image"]} for item in json_training]
        val_files += [{"image": item["image"]} for item in json_val]

    # datalist, val_files = setup_pretraining_data_SwinUNETR(args)
    print("Dataset all training: number of data: {}".format(len(datalist)))
    print("Dataset all validation: number of data: {}".format(len(val_files)))

    train_transforms = Compose(
        [
            LoadImaged(keys=["image"]),
            # AddChanneld(keys=["image"]),
            EnsureChannelFirstd(keys=["image"]),
            Orientationd(keys=["image"], axcodes="RAS"),
            ScaleIntensityRanged(
                keys=["image"], a_min=args.a_min, a_max=args.a_max, b_min=args.b_min, b_max=args.b_max, clip=True
            ),
            SpatialPadd(keys="image", spatial_size=[args.roi_x, args.roi_y, args.roi_z]),
            CropForegroundd(keys=["image"], source_key="image", k_divisible=[args.roi_x, args.roi_y, args.roi_z]),
            RandSpatialCropSamplesd(
                keys=["image"],
                roi_size=[args.roi_x, args.roi_y, args.roi_z],
                num_samples=args.sw_batch_size,
                random_center=True,
                random_size=False,
            ),
            ToTensord(keys=["image"]),
        ]
    )
    val_transforms = Compose(
        [
            LoadImaged(keys=["image"]),
            # AddChanneld(keys=["image"]),
            EnsureChannelFirstd(keys=["image"]),
            Orientationd(keys=["image"], axcodes="RAS"),
            ScaleIntensityRanged(
                keys=["image"], a_min=args.a_min, a_max=args.a_max, b_min=args.b_min, b_max=args.b_max, clip=True
            ),
            SpatialPadd(keys="image", spatial_size=[args.roi_x, args.roi_y, args.roi_z]),
            CropForegroundd(keys=["image"], source_key="image", k_divisible=[args.roi_x, args.roi_y, args.roi_z]),
            RandSpatialCropSamplesd(
                keys=["image"],
                roi_size=[args.roi_x, args.roi_y, args.roi_z],
                num_samples=args.sw_batch_size,
                random_center=True,
                random_size=False,
            ),
            ToTensord(keys=["image"]),
        ]
    )

    if args.cache_dataset:
        print("Using MONAI Cache Dataset")
        train_ds = CacheDataset(data=datalist, transform=train_transforms, cache_rate=0.5, num_workers=num_workers)
    elif args.smartcache_dataset:
        print("Using MONAI SmartCache Dataset")
        train_ds = SmartCacheDataset(
            data=datalist,
            transform=train_transforms,
            replace_rate=1.0,
            cache_num=2 * args.batch_size * args.sw_batch_size,
        )
    else:
        print("Using generic dataset")
        train_ds = Dataset(data=datalist, transform=train_transforms)

    if args.distributed:
        train_sampler = DistributedSampler(dataset=train_ds, even_divisible=True, shuffle=True)
    else:
        train_sampler = None
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, num_workers=args.num_workers, sampler=train_sampler, drop_last=True
    )

    val_ds = Dataset(data=val_files, transform=val_transforms)
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, num_workers=args.num_workers, shuffle=False, drop_last=True
    )

    return train_loader, val_loader
