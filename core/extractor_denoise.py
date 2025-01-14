import torch.nn as nn
from cell_net import Decom, Hfre, Lfre,ConvFuse, BasicStage
import torch
from core.atten import AttentionModule
from HFDB import HLFDB,HLFDB2,HLFDB3

import torch.nn as nn


class ConvTokenizer(nn.Module):
    def __init__(self, embedding_dim=128):
        super(ConvTokenizer, self).__init__()
        self.block = nn.Sequential(
            nn.Conv2d(3, embedding_dim // 2, # 64
                      kernel_size=(3, 3),
                      stride=(2, 2),
                      padding=(1, 1),
                      bias=False),
            nn.BatchNorm2d(embedding_dim // 2),
            nn.ReLU(inplace=True),
            nn.Conv2d(embedding_dim // 2, # 64
                      embedding_dim // 2,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=(1, 1),
                      bias=False),
            nn.BatchNorm2d(embedding_dim // 2),
            nn.ReLU(inplace=True),
            nn.Conv2d(embedding_dim // 2,
                      embedding_dim, # 128
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=(1, 1),
                      bias=False),
            nn.BatchNorm2d(embedding_dim),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=(3, 3),
                         stride=(2, 2),
                         padding=(1, 1),
                         dilation=(1, 1))
        )
    def forward(self, x):
        return self.block(x)



class FrequencyExtractor(nn.Module):
    def __init__(self,
                 blocks,
                 dims,
                 channels=128,
                 output_dim=128,
                 *args, **kwargs):
        super(FrequencyExtractor, self).__init__()

        self.tokenizer = ConvTokenizer(embedding_dim=channels)

        self.conv_decom = Decom(embedding_dim_in=channels)

        self.hfre = Hfre(embedding_dim_in=channels,
                         embedding_dim_out=dims[0])

        self.lfre = Lfre(embedding_dim_in=channels,
                         embedding_dim_out=dims[0])
        self.fuse = ConvFuse(embedding_dim_in=channels,
                             embedding_dim_out=dims[0])

        self.stages = nn.ModuleList()
        for i in range(0, len(blocks)):
            stage = BasicStage(num_blocks=blocks[i],
                               embedding_dims=dims[i:i + 2],
                               stochastic_depth_rate=0.1,
                               downsample=(i + 1 < len(blocks)))
            self.stages.append(stage)

        else:
            self.head = None
        self.apply(self.init_weight)
        # self.linear = nn.Conv2d(in_channels = 256, out_channels = output_dim , kernel_size= 1)
        # self.linear = nn.Conv2d(in_channels=128, out_channels=output_dim, kernel_size=1)
        self.pool = nn.MaxPool2d(2)
    def forward(self, x):
        x = self.tokenizer(x)
        h_fre, l_fre = self.conv_decom(x)
        h = self.hfre(l_fre)
        l = self.lfre(h_fre)
        x_fuse = torch.cat([h,l],dim=1)
        x = self.fuse(x_fuse)
        x = self.pool(x).permute(0, 2, 3, 1)
        for stage in self.stages:
            x = stage(x)
        if self.head is None:
            x = x.permute(0, 3, 1, 2).contiguous()
            # x = self.linear(x)
            return x

    @staticmethod
    def init_weight(m):
        if isinstance(m, (nn.Linear, nn.Conv1d)):
            nn.init.trunc_normal_(m.weight, std=.02)
            if isinstance(m, (nn.Linear, nn.Conv1d)) and m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.bias, 0)
            nn.init.constant_(m.weight, 1.0)
        elif isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
        elif isinstance(m, nn.BatchNorm2d):
            nn.init.constant_(m.weight, 1.)
            nn.init.constant_(m.bias, 0.)





def _get_model(arch, pretrained, progress, classifier_head, blocks, dims,output_dim, *args, **kwargs):
    print('use FrequencyExtractor')
    model = FrequencyExtractor(blocks=blocks, dims=dims,
                    classifier_head=classifier_head, output_dim = output_dim, *args, **kwargs)
    return model

def get_model(pretrained=False, progress=False, classifier_head=False, *args, **kwargs):
    return _get_model('', pretrained=pretrained, progress=progress,
                blocks=[3],dims=[256], channels=128,
                classifier_head=classifier_head,
                *args, **kwargs)


def get_enhance():
    model = AttentionModule()
    return model





