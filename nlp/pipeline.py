from models.intent_classifier import IntentClassifier
from utils.entity_extractor import extract_entities
from utils.context_manager import ContextManager


class NLPBrain:

    def __init__(self):

        # ML intent classifier
        self.classifier = IntentClassifier()

        # Context memory
        self.context = ContextManager() 

    # -------------------------
    # Main prediction pipeline
    # -------------------------
    def predict(self, text: str):

        # -------------------------
        # 1. Intent classification
        # -------------------------
        result = self.classifier.predict(text)

        intent                 = result["intent"]
        confidence             = result["confidence"]
        requires_clarification = result["requires_clarification"]

        # -------------------------
        # 2. Entity extraction
        # -------------------------
        entities = extract_entities(text, intent)

        # -------------------------
        # 3. Context handling
        # -------------------------
        context = self.context.get_context()

        is_follow_up = self.context.is_follow_up(text)
        reference    = self.context.resolve_reference(text)

        context_used = False

        if is_follow_up and context["last_intent"]:

            context_used = True

            # Only inherit intent if classifier isn't confident
            if confidence < 0.75:
                intent = context["last_intent"]

            # Re-extract entities for resolved intent
            fresh = extract_entities(text, intent)

            # Resolve bare number BEFORE merging with slots
            if "bare_number" in fresh and "duration" in context["slots"]:
                last_unit = context["slots"]["duration"].split()[-1]
                fresh["duration"] = f"{fresh.pop('bare_number')} {last_unit}"

            # Now merge — fresh entities take priority over old slots
            merged = dict(context["slots"])
            merged.update(fresh)
            entities = merged

        elif reference:
            context_used = True
            # Only inherit intent from reference if classifier isn't confident
            if confidence < 0.75:
                intent = reference.get("intent", intent)
            merged = reference.get("entities", {})
            merged.update(entities)
            entities = merged

        # -------------------------
        # 4. Update memory
        # -------------------------
        self.context.update_context(intent, entities, text)

        print(f"DEBUG final entities: {entities}")

        # -------------------------
        # 5. Final structured output
        # -------------------------
        return {
            "intent"                : intent,
            "confidence"            : confidence,
            "entities"              : entities,
            "requires_clarification": requires_clarification,
            "context_used"          : context_used
        }