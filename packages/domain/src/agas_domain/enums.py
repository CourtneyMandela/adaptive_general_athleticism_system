from enum import StrEnum


class Confidence(StrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ObservationSource(StrEnum):
    USER_REPORT = "user_report"
    WORKOUT_RESULT = "workout_result"
    TEST_RESULT = "test_result"
    WEARABLE = "wearable"
    MANUAL_ENTRY = "manual_entry"
    IMPORTED_ACTIVITY = "imported_activity"
    COACH_EVALUATION = "coach_evaluation"


class CapabilityDomain(StrEnum):
    AEROBIC_CAPACITY = "aerobic_capacity"
    REPEATED_EFFORT_CAPACITY = "repeated_effort_capacity"
    MAXIMUM_STRENGTH = "maximum_strength"
    RELATIVE_STRENGTH = "relative_strength"
    MUSCULAR_ENDURANCE = "muscular_endurance"
    EXPLOSIVE_POWER = "explosive_power"
    ACCELERATION = "acceleration"
    HIGH_SPEED_RUNNING = "high_speed_running"
    DECELERATION = "deceleration"
    CHANGE_OF_DIRECTION = "change_of_direction"
    LOADED_LOCOMOTION = "loaded_locomotion"
    MOBILITY = "mobility"
    MOVEMENT_CONTROL = "movement_control"
    BALANCE_COORDINATION = "balance_coordination"
    MOVEMENT_VERSATILITY = "movement_versatility"
    TISSUE_EXPOSURE = "tissue_exposure"
    NOVELTY_TRANSFER = "novelty_transfer"


class CostLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ImpactLevel(StrEnum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class Loadability(StrEnum):
    LIMITED = "limited"
    MODERATE = "moderate"
    HIGH = "high"


class AdaptationRelationshipType(StrEnum):
    PREREQUISITE = "prerequisite"
    PARTIAL_PREREQUISITE = "partial_prerequisite"
    POTENTIATING = "potentiating"
    INTERFERING = "interfering"
    COMPLEMENTARY = "complementary"
    MAINTENANCE_COMPATIBLE = "maintenance_compatible"
    COMPETING_FOR_RECOVERY = "competing_for_recovery"
    SKILL_DEPENDENT = "skill_dependent"


class EvidenceStrength(StrEnum):
    INSUFFICIENT = "insufficient"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class Applicability(StrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class AssessmentIntensity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    MAXIMAL = "maximal"


class AssessmentDecision(StrEnum):
    SELECTED = "selected"
    DEFERRED = "deferred"
    EXCLUDED = "excluded"


class AssessmentReason(StrEnum):
    ELIGIBLE = "eligible"
    MISSING_EQUIPMENT = "missing_equipment"
    MISSING_BODY_MASS = "missing_body_mass"
    INSUFFICIENT_TRAINING_HISTORY = "insufficient_training_history"
    MISSING_SKILL = "missing_skill"
    MISSING_RECENT_EXPOSURE = "missing_recent_exposure"
    SYMPTOM_CONSTRAINT = "symptom_constraint"
    INJURY_CONSTRAINT = "injury_constraint"
    HEALTH_SCREENING_CONSTRAINT = "health_screening_constraint"


class ComparisonDirection(StrEnum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class CompetencyStatus(StrEnum):
    BELOW_FLOOR = "below_floor"
    MEETS_FLOOR = "meets_floor"
    ABOVE_FLOOR = "above_floor"
    UNKNOWN = "unknown"
    STALE = "stale"
    INCOMPARABLE = "incomparable"


class TrainingPriorityState(StrEnum):
    DEVELOP = "develop"
    MAINTAIN = "maintain"
    EXPOSE = "expose"
    DEFER = "defer"


class PlanningReason(StrEnum):
    COMPETENCY_DEFICIT = "competency_deficit"
    COMPETENCY_MET = "competency_met"
    COMPARATIVE_ADVANTAGE = "comparative_advantage"
    INFORMATION_GAP = "information_gap"
    INTRODUCTORY_EXPOSURE = "introductory_exposure"
    SAFETY_CONSTRAINT = "safety_constraint"
    PREREQUISITE_NOT_MET = "prerequisite_not_met"
    LOWER_PRIORITY = "lower_priority"


class ResolutionStatus(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    INFEASIBLE = "infeasible"


class ResolutionIssueCode(StrEnum):
    MISSING_EQUIPMENT = "missing_equipment"
    ADAPTATION_MISMATCH = "adaptation_mismatch"
    MOVEMENT_PATTERN_MISMATCH = "movement_pattern_mismatch"
    LOADING_TYPE_MISMATCH = "loading_type_mismatch"
    INSUFFICIENT_LOADABILITY = "insufficient_loadability"
    VELOCITY_MISMATCH = "velocity_mismatch"
    SKILL_CONSTRAINT = "skill_constraint"
    IMPACT_CONSTRAINT = "impact_constraint"
    STABILITY_CONSTRAINT = "stability_constraint"
    FATIGUE_CONSTRAINT = "fatigue_constraint"
    SORENESS_CONSTRAINT = "soreness_constraint"
    CONTRAINDICATION = "contraindication"
    OUTDOOR_ACCESS_REQUIRED = "outdoor_access_required"
    INSUFFICIENT_SPACE = "insufficient_space"
    NOISE_CONSTRAINT = "noise_constraint"
    BELOW_PARTIAL_THRESHOLD = "below_partial_threshold"
    NO_CANDIDATE = "no_candidate"


class BlockPlanStatus(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    INFEASIBLE = "infeasible"


class BlockIssueCode(StrEnum):
    MINIMUM_RESOURCE_UNMET = "minimum_resource_unmet"
    TARGET_RESOURCE_SHORTFALL = "target_resource_shortfall"
    PARTIAL_EXERCISE_RESOLUTION = "partial_exercise_resolution"
    INFEASIBLE_EXERCISE_RESOLUTION = "infeasible_exercise_resolution"


class WeeklyPlanStatus(StrEnum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"


class SchedulingIssueCode(StrEnum):
    NO_MATCHING_ENVIRONMENT = "no_matching_environment"
    WINDOW_TOO_SHORT = "window_too_short"
    DAILY_SESSION_LIMIT = "daily_session_limit"
    HIGH_FATIGUE_DAILY_LIMIT = "high_fatigue_daily_limit"
    RECOVERY_CONSTRAINT = "recovery_constraint"
    NO_AVAILABLE_WINDOW = "no_available_window"


class ReadinessLevel(StrEnum):
    READY = "ready"
    LIMITED = "limited"
    NOT_READY = "not_ready"


class SafetySignalClass(StrEnum):
    MODIFY = "modify"
    ESCALATE = "escalate"


class SafetyGateTiming(StrEnum):
    PRE_SESSION = "pre_session"
    POST_SESSION = "post_session"


class SafetyGateOutcome(StrEnum):
    PROCEED = "proceed"
    MODIFY = "modify"
    HOLD = "hold"
    STOP_AND_ESCALATE = "stop_and_escalate"


class PrescriptionModification(StrEnum):
    REDUCE_VOLUME = "reduce_volume"
    REDUCE_INTENSITY = "reduce_intensity"
    REMOVE_HIGH_IMPACT = "remove_high_impact"
    REMOVE_HIGH_SPEED = "remove_high_speed"
    RESTRICT_RANGE = "restrict_range"
    SHORTEN_SESSION = "shorten_session"
    REVIEWED_SUBSTITUTION_REQUIRED = "reviewed_substitution_required"


class SessionExecutionStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    NOT_STARTED = "not_started"
    STOPPED_SAFETY = "stopped_safety"


class SessionSection(StrEnum):
    PREPARATION = "preparation"
    PRIMARY = "primary"
    ACCESSORY = "accessory"
    CONDITIONING = "conditioning"
    COOLDOWN = "cooldown"
    OTHER = "other"


class ProgressionOutcome(StrEnum):
    PROGRESS = "progress"
    REPEAT = "repeat"
    HOLD = "hold"
    REVIEW_REQUIRED = "review_required"


class ProgressionDimension(StrEnum):
    LOAD = "load"
    REPETITIONS = "repetitions"
    SETS = "sets"
    DURATION = "duration"
    DENSITY = "density"
    RANGE_OF_MOTION = "range_of_motion"
    SPEED = "speed"
    COMPLEXITY = "complexity"
    MODALITY = "modality"


class ExposureType(StrEnum):
    RUNNING = "running"
    HIGH_SPEED_RUNNING = "high_speed_running"
    JUMPING = "jumping"
    LANDING = "landing"
    CHANGE_OF_DIRECTION = "change_of_direction"
    HIGH_IMPACT_PLYOMETRICS = "high_impact_plyometrics"


class ExposureValidationOutcome(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class BlockReviewOutcome(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    NOT_SUPPORTED = "not_supported"
    INCONCLUSIVE = "inconclusive"
