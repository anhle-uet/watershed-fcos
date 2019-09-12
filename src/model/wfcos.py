"""Watershed FCOS.

Hybrid using watershed energy map instead of centerness from FCOS.
"""
import torch.nn as nn
from .resnet import ResNet
from .fpn import FPN
from .wfcos_head import WFCOSHead
import mmcv.runner.checkpoint as checkpoint

class WFCOS(nn.Module):
    def __init__(self, backbone_cfg, neck_cfg, head_cfg):
        """Initializes the watershed FCOS model

        Args:
            backbone_cfg (dict): The configuration of the backbone.
            neck_cfg (dict): The configuration of the neck.
            head_cfg (dict): The configuration of the head.
            pretrained (str or None): Address of the pretrained model. If None,
                then does not use pretrained. Defaults to None.
        """
        super(WFCOS, self).__init__()
        self.backbone = ResNet(**backbone_cfg)

        self.neck = FPN(**neck_cfg)

        self.head = WFCOSHead(**head_cfg)

    def forward(self, x):
        x = self.backbone(x)
        x = self.neck(x)
        x = self.head(x)

        return x

    def load_backbone_pretrained(self, pretrained):
        self.backbone.init_weights(pretrained)

    def init_weights(self, backbone, neck, head):
        """Initialize the specified weights.

        Args:
            backbone (bool): Whether or not to initialize the backbone.
            neck (bool): Whether or not to initialize the neck.
            head (bool): Whether or not to initialize the head.
        """
        if backbone:
            self.backbone.init_weights()
        if neck:
            self.neck.init_weights()
        if head:
            self.head.init_weights()
