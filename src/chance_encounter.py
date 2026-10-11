"""P01 deterministic self-report entertainment rules; no ML, I/O or probability claims."""
from dataclasses import dataclass
from typing import Mapping

RULE_VERSION = 'p01_equal_mean_v1'

# Machine keys are stable; translated display text never enters the calculation.
OPTIONS = {
    'relationship': {'friend':'朋友','classmate':'同学','coworker':'同事','acquaintance':'熟人','stranger':'陌生人','other':'其他'},
    'distance': {'same_area':'经常处于同一建筑或区域','walkable':'步行可达','city_far':'同一城市但距离较远','different_city':'不同城市','unknown':'不确定'},
    'frequency': {'zero':'0次','one_two':'1–2次','three_five':'3–5次','six_plus':'6次及以上','unknown':'不记得'},
    'recency': {'day':'最近24小时','week':'最近7天','month':'最近30天','older':'超过30天','never':'从未偶遇','unknown':'不确定'},
    'area': {'often':'经常去相同区域','sometimes':'偶尔去相同区域','rare':'很少重合','unknown':'不确定'},
    'timing': {'often':'经常在相似时间活动','sometimes':'偶尔相似','different':'差异较大','unknown':'不确定'},
    'arrangement': {'yes':'已经明确约定','no':'没有约定','unknown':'不确定'},
}
QUESTIONS = {
    'relationship':'两个人是什么关系？', 'distance':'两个人大致相距多远？',
    'frequency':'过去30天偶然遇见过多少次？', 'recency':'最近一次偶然遇见是在什么时候？',
    'area':'日常活动区域重合程度如何？', 'timing':'平时活动时间是否相似？',
    'arrangement':'未来24小时是否已经安排见面？',
}
FACTOR_NAMES = {'frequency':'历史偶遇','distance':'距离因素','area':'活动区域','timing':'时间规律','recency':'最近一次偶遇'}
# Equal weights deliberately avoid unsupported claims of empirically optimal weights.
# Unknown/missing is OMITTED from numerator AND denominator; never imputed as zero.
POINTS = {
    'frequency': {'zero':0,'one_two':35,'three_five':70,'six_plus':100},
    'distance': {'same_area':100,'walkable':75,'city_far':30,'different_city':0},
    'area': {'often':100,'sometimes':55,'rare':0},
    'timing': {'often':100,'sometimes':55,'different':0},
    'recency': {'day':100,'week':75,'month':45,'older':15,'never':0},
}
DESCRIPTIONS = {
    'frequency':'仅统计你填写的未提前安排的偶遇次数。历史记录更多，在这套娱乐规则中线索更强。',
    'distance':'只按你描述的大致距离计分，没有获取住址或定位。通常距离更近，在规则中线索更强。',
    'area':'这是你对日常区域的主观判断，不是实际 GPS 观测。区域重合更多，在规则中线索更强。',
    'timing':'只依据你填写的平时活动时间相似度，不代表系统知道双方日程。',
    'recency':'只依据你填写的最近一次偶遇时间；更近的记录在规则中线索更强。',
}


@dataclass(frozen=True)
class Questionnaire:
    relationship: str | None = None
    distance: str | None = None
    frequency: str | None = None
    recency: str | None = None
    area: str | None = None
    timing: str | None = None
    arrangement: str | None = None

    @classmethod
    def from_mapping(cls, values: Mapping):
        if not isinstance(values, Mapping) or set(values)-set(OPTIONS):
            raise ValueError('问卷字段不符合 P01 结构。')
        return cls(**values)


@dataclass(frozen=True)
class Issue:
    field: str
    message: str


@dataclass(frozen=True)
class Keyword:
    field: str
    name: str
    source: str
    explanation: str
    direction: str
    points: int


@dataclass(frozen=True)
class EntertainmentResult:
    status: str
    message: str
    score: int | None = None
    level: str | None = None
    keywords: tuple[Keyword, ...] = ()
    issues: tuple[Issue, ...] = ()
    unknown_fields: tuple[str, ...] = ()
    rule_version: str = RULE_VERSION


def evaluate_questionnaire(answers: Questionnaire) -> EntertainmentResult:
    """Stable UI/engine interface; future engines must disclose their own provenance.

    Index = round-half-up(sum(known factor points) / known factor count).
    Require >=3 of the five historical/usual-routine factors. Relationship is
    description only; arrangement is an exclusion gate, never a scored feature.
    Levels:0..34偏低,35..69中等,70..100偏高. All points/levels are design choices.
    """
    if not isinstance(answers, Questionnaire):
        raise TypeError('需要 Questionnaire 输入。')
    invalid = tuple(Issue(field,'请选择有效选项。') for field, choices in OPTIONS.items()
                    if (value:=getattr(answers,field)) is not None
                    and (not isinstance(value,str) or value not in choices))
    if invalid:
        return EntertainmentResult('invalid','请检查问卷选项。',issues=invalid)
    if answers.arrangement == 'yes':
        return EntertainmentResult('out_of_scope','本实验只研究没有提前约定的偶然相遇，已经安排的见面不在本次预测范围内。')
    if answers.arrangement != 'no':
        return EntertainmentResult('needs_confirmation','请先确认未来24小时没有明确约定见面，再继续体验。')
    if answers.relationship is None:
        return EntertainmentResult('invalid','请选择两个人的关系。',issues=(Issue('relationship','请选择关系；关系类型不会加减分。'),))
    inconsistent = ((answers.frequency in {'one_two','three_five','six_plus'} and answers.recency in {'older','never'})
                    or (answers.frequency == 'zero' and answers.recency in {'day','week','month'}))
    if inconsistent:
        return EntertainmentResult('inconsistent','过去30天的次数与最近一次偶遇时间不一致，请检查这两项。',
                                   issues=(Issue('frequency','次数与最近一次时间需一致。'),Issue('recency','请只填写未提前安排的偶遇。')))
    known = [(field, values[getattr(answers,field)]) for field, values in POINTS.items() if getattr(answers,field) in values]
    unknown = tuple(field for field in POINTS if getattr(answers,field) not in POINTS[field])
    if len(known) < 3:
        return EntertainmentResult('insufficient','至少补充3项有效历史或日常线索后才能计算；不确定和未填写项不会当成零分。',unknown_fields=unknown)
    score = (2*sum(points for _,points in known)+len(known))//(2*len(known))
    level = '偏低' if score < 35 else '中等' if score < 70 else '偏高'
    keywords = tuple(Keyword(field,FACTOR_NAMES[field],'用户填写：'+OPTIONS[field][getattr(answers,field)],
                             DESCRIPTIONS[field],'较强线索' if points>=70 else '一般线索' if points>=30 else '较弱线索',points)
                     for field,points in known)
    message = (f'根据你填写的{OPTIONS["relationship"][answers.relationship]}关系及{len(known)}项历史或日常线索，'
               f'这套规则给出“{level}”的趣味倾向。未来是否真的碰见，仍然充满偶然性。')
    return EntertainmentResult('ready',message,score,level,keywords,unknown_fields=unknown)
