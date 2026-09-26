from .v0001_vocabulary import upgrade
from .v0002_learning_content import upgrade as upgrade_learning_content
from .v0003_beginner_grammar import upgrade as upgrade_beginner_grammar
from .v0004_external_examples import upgrade as upgrade_external_examples
from .v0005_vocabulary_search import upgrade as upgrade_vocabulary_search
from .v0006_grammar_expansion import upgrade as upgrade_grammar_expansion
from .v0007_online_grammar import upgrade as upgrade_online_grammar
from .v0008_supine_example import upgrade as upgrade_supine_example
from .v0009_repair_supine_example import upgrade as upgrade_repair_supine_example


def upgrade_all(app):
	return [
		upgrade(app),
		upgrade_learning_content(app),
		upgrade_beginner_grammar(app),
		upgrade_external_examples(app),
		upgrade_vocabulary_search(app),
		upgrade_grammar_expansion(app),
		upgrade_online_grammar(app),
		upgrade_supine_example(app),
		upgrade_repair_supine_example(app),
	]


__all__ = [
	"upgrade",
	"upgrade_all",
	"upgrade_beginner_grammar",
	"upgrade_external_examples",
	"upgrade_learning_content",
	"upgrade_vocabulary_search",
	"upgrade_grammar_expansion",
	"upgrade_online_grammar",
	"upgrade_supine_example",
	"upgrade_repair_supine_example",
]