1. 我在html和css中都删除了冠军奖杯相关的内容，我不需要这个冠军奖杯了，在js中也将其相关代码删除掉。
2. 每个round登记分数后，选手的player-score应该累积。然而现在的版本中每登录一次分数，player-score会被更新而不是累积。
3. 淘汰赛的晋级规则有所修改。原先的AB组更名为E组，E组由A组#1 B组#2 C组#2 D组#1组成，原先的CD组更名为F组，F组由A组#2 B组#1 C组#1 D组#2组成。比赛先后顺序是ABCDEF组，最后是决赛。
4. 在初始化的时候，淘汰赛第一阶段参与的16个玩家的背景板都会高亮。我不需要全部的高亮，初始化之后应该开始A组的比赛，只高亮A组四个选手即可。在A组Settle后自动对下一组的选手进行高亮。
5. ABCDEF组选手的排序规则为优先考虑PT大小，PT相同者看累积的player-score大小。决赛阶段排序规则不一样，决赛组选手的排序规则只看PT，player-score不做累计。如果有PT相同的情况，则进行加赛，进入加赛阶段后不计PT，只累计player-score。
6. 在ABCDEF组，晋级角色有绿色高亮效果，但我希望Final阶段有不同的光效，冠军应该闪金光，player-points字段替换成🥇emoji，亚军季军以此类推。
7. 在使用init命令初始化的时候，程序只修改了tournament-title的文字。然而原先tournament-title字段中的stage-indicator title-text都消失掉了。请修复这个问题。