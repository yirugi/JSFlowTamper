"use strict";
/**
 * Copyright 2018 Google Inc. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the 'License');
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an 'AS IS' BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.Accessibility = void 0;
class Accessibility {
    constructor(client) {
        this._client = client;
    }
    async snapshot(options = {}) {
        const { interestingOnly = true, root = null } = options;
        const { nodes } = await this._client.send('Accessibility.getFullAXTree');
        let backendNodeId = null;
        if (root) {
            const { node } = await this._client.send('DOM.describeNode', {
                objectId: root._remoteObject.objectId,
            });
            backendNodeId = node.backendNodeId;
        }
        const defaultRoot = AXNode.createTree(nodes);
        let needle = defaultRoot;
        if (backendNodeId) {
            needle = defaultRoot.find((node) => node.payload.backendDOMNodeId === backendNodeId);
            if (!needle)
                return null;
        }
        if (!interestingOnly)
            return this.serializeTree(needle)[0];
        const interestingNodes = new Set();
        this.collectInterestingNodes(interestingNodes, defaultRoot, false);
        if (!interestingNodes.has(needle))
            return null;
        return this.serializeTree(needle, interestingNodes)[0];
    }
    serializeTree(node, whitelistedNodes) {
        const children = [];
        for (const child of node.children)
            children.push(...this.serializeTree(child, whitelistedNodes));
        if (whitelistedNodes && !whitelistedNodes.has(node))
            return children;
        const serializedNode = node.serialize();
        if (children.length)
            serializedNode.children = children;
        return [serializedNode];
    }
    collectInterestingNodes(collection, node, insideControl) {
        if (node.isInteresting(insideControl))
            collection.add(node);
        if (node.isLeafNode())
            return;
        insideControl = insideControl || node.isControl();
        for (const child of node.children)
            this.collectInterestingNodes(collection, child, insideControl);
    }
}
exports.Accessibility = Accessibility;
class AXNode {
    constructor(payload) {
        this.children = [];
        this._richlyEditable = false;
        this._editable = false;
        this._focusable = false;
        this._hidden = false;
        this.payload = payload;
        this._name = this.payload.name ? this.payload.name.value : '';
        this._role = this.payload.role ? this.payload.role.value : 'Unknown';
        for (const property of this.payload.properties || []) {
            if (property.name === 'editable') {
                this._richlyEditable = property.value.value === 'richtext';
                this._editable = true;
            }
            if (property.name === 'focusable')
                this._focusable = property.value.value;
            if (property.name === 'hidden')
                this._hidden = property.value.value;
        }
    }
    _isPlainTextField() {
        if (this._richlyEditable)
            return false;
        if (this._editable)
            return true;
        return (this._role === 'textbox' ||
            this._role === 'ComboBox' ||
            this._role === 'searchbox');
    }
    _isTextOnlyObject() {
        const role = this._role;
        return role === 'LineBreak' || role === 'text' || role === 'InlineTextBox';
    }
    _hasFocusableChild() {
        if (this._cachedHasFocusableChild === undefined) {
            this._cachedHasFocusableChild = false;
            for (const child of this.children) {
                if (child._focusable || child._hasFocusableChild()) {
                    this._cachedHasFocusableChild = true;
                    break;
                }
            }
        }
        return this._cachedHasFocusableChild;
    }
    find(predicate) {
        if (predicate(this))
            return this;
        for (const child of this.children) {
            const result = child.find(predicate);
            if (result)
                return result;
        }
        return null;
    }
    isLeafNode() {
        if (!this.children.length)
            return true;
        // These types of objects may have children that we use as internal
        // implementation details, but we want to expose them as leaves to platform
        // accessibility APIs because screen readers might be confused if they find
        // any children.
        if (this._isPlainTextField() || this._isTextOnlyObject())
            return true;
        // Roles whose children are only presentational according to the ARIA and
        // HTML5 Specs should be hidden from screen readers.
        // (Note that whilst ARIA buttons can have only presentational children, HTML5
        // buttons are allowed to have content.)
        switch (this._role) {
            case 'doc-cover':
            case 'graphics-symbol':
            case 'img':
            case 'Meter':
            case 'scrollbar':
            case 'slider':
            case 'separator':
            case 'progressbar':
                return true;
            default:
                break;
        }
        // Here and below: Android heuristics
        if (this._hasFocusableChild())
            return false;
        if (this._focusable && this._name)
            return true;
        if (this._role === 'heading' && this._name)
            return true;
        return false;
    }
    isControl() {
        switch (this._role) {
            case 'button':
            case 'checkbox':
            case 'ColorWell':
            case 'combobox':
            case 'DisclosureTriangle':
            case 'listbox':
            case 'menu':
            case 'menubar':
            case 'menuitem':
            case 'menuitemcheckbox':
            case 'menuitemradio':
            case 'radio':
            case 'scrollbar':
            case 'searchbox':
            case 'slider':
            case 'spinbutton':
            case 'switch':
            case 'tab':
            case 'textbox':
            case 'tree':
                return true;
            default:
                return false;
        }
    }
    isInteresting(insideControl) {
        const role = this._role;
        if (role === 'Ignored' || this._hidden)
            return false;
        if (this._focusable || this._richlyEditable)
            return true;
        // If it's not focusable but has a control role, then it's interesting.
        if (this.isControl())
            return true;
        // A non focusable child of a control is not interesting
        if (insideControl)
            return false;
        return this.isLeafNode() && !!this._name;
    }
    serialize() {
        const properties = new Map();
        for (const property of this.payload.properties || [])
            properties.set(property.name.toLowerCase(), property.value.value);
        if (this.payload.name)
            properties.set('name', this.payload.name.value);
        if (this.payload.value)
            properties.set('value', this.payload.value.value);
        if (this.payload.description)
            properties.set('description', this.payload.description.value);
        const node = {
            role: this._role,
        };
        const userStringProperties = [
            'name',
            'value',
            'description',
            'keyshortcuts',
            'roledescription',
            'valuetext',
        ];
        const getUserStringPropertyValue = (key) => properties.get(key);
        for (const userStringProperty of userStringProperties) {
            if (!properties.has(userStringProperty))
                continue;
            node[userStringProperty] = getUserStringPropertyValue(userStringProperty);
        }
        const booleanProperties = [
            'disabled',
            'expanded',
            'focused',
            'modal',
            'multiline',
            'multiselectable',
            'readonly',
            'required',
            'selected',
        ];
        const getBooleanPropertyValue = (key) => properties.get(key);
        for (const booleanProperty of booleanProperties) {
            // WebArea's treat focus differently than other nodes. They report whether their frame  has focus,
            // not whether focus is specifically on the root node.
            if (booleanProperty === 'focused' && this._role === 'WebArea')
                continue;
            const value = getBooleanPropertyValue(booleanProperty);
            if (!value)
                continue;
            node[booleanProperty] = getBooleanPropertyValue(booleanProperty);
        }
        const tristateProperties = ['checked', 'pressed'];
        for (const tristateProperty of tristateProperties) {
            if (!properties.has(tristateProperty))
                continue;
            const value = properties.get(tristateProperty);
            node[tristateProperty] =
                value === 'mixed' ? 'mixed' : value === 'true' ? true : false;
        }
        const numericalProperties = [
            'level',
            'valuemax',
            'valuemin',
        ];
        const getNumericalPropertyValue = (key) => properties.get(key);
        for (const numericalProperty of numericalProperties) {
            if (!properties.has(numericalProperty))
                continue;
            node[numericalProperty] = getNumericalPropertyValue(numericalProperty);
        }
        const tokenProperties = [
            'autocomplete',
            'haspopup',
            'invalid',
            'orientation',
        ];
        const getTokenPropertyValue = (key) => properties.get(key);
        for (const tokenProperty of tokenProperties) {
            const value = getTokenPropertyValue(tokenProperty);
            if (!value || value === 'false')
                continue;
            node[tokenProperty] = getTokenPropertyValue(tokenProperty);
        }
        return node;
    }
    static createTree(payloads) {
        const nodeById = new Map();
        for (const payload of payloads)
            nodeById.set(payload.nodeId, new AXNode(payload));
        for (const node of nodeById.values()) {
            for (const childId of node.payload.childIds || [])
                node.children.push(nodeById.get(childId));
        }
        return nodeById.values().next().value;
    }
}
