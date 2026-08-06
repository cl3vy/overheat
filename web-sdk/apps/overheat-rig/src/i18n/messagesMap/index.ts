import { mergeMessagesMaps } from 'utils-shared/i18n';
import { messagesMap as messagesMapUiPixi } from 'components-ui-pixi';
import { messagesMap as messagesMapUiHtml } from 'components-ui-html';

import en from './en';
import es from './es';
import pt from './pt';
import ja from './ja';
import zh from './zh';

const messagesMapGame = {
	en,
	es,
	pt,
	ja,
	zh,
} as unknown as typeof messagesMapUiHtml;

const messagesMap = mergeMessagesMaps([messagesMapGame, messagesMapUiPixi, messagesMapUiHtml]);

export default messagesMap;
