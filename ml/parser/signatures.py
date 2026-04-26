import dspy
import pydantic


class Program(pydantic.BaseModel):
    composer: str  # 작곡가 원어명 (영문)
    piece: str     # 곡명 원어명 (영문), 작품번호 포함


class ProgramExtractor(dspy.Signature):
    """클래식 공연 작품소개 텍스트에서 연주 프로그램 정보를 추출합니다.

    각 곡의 작곡가(composer)와 곡명(piece, 작품번호 포함)을 추출합니다.
    한글/영문 병기된 경우 원어(영문) 기준으로 하나만 추출합니다.
    동일한 곡이 한글과 영문으로 반복되면 하나의 항목으로 합칩니다.
    프로그램 정보가 없는 경우(출연자 프로필만 있는 등) 빈 리스트를 반환합니다.
    """
    detail_text: str = dspy.InputField(desc="공연 작품소개 텍스트 (한글/영문 혼용)")
    programs: list[Program] = dspy.OutputField(desc="추출된 프로그램 목록. 한글/영문 병기 시 원어(영문) 기준 하나만 추출.")
