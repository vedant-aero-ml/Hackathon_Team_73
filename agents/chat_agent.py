"""
Chat Agent — Two-step pandas code-execution Q&A + in-place updates.

READ path  (query):  LLM generates pandas expression → eval() → format answer.
WRITE path (update): LLM generates pandas statement → exec() on df copy →
                     recompute Status/Reason → confirm change.

Answers and updates are always grounded in real data — hallucination is impossible.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config.settings import MAX_TOKENS, MODEL_NAME


@dataclass
class ChatResult:
    reply: str
    updated_df: pd.DataFrame | None  # None for READ, mutated df for WRITE


class ChatAgent:
    """
    Handles natural-language queries AND updates over a vendor master DataFrame.

    run() args:
        user_message         (str)        — the user's latest message
        conversation_history (list[dict]) — prior turns as {role, content} dicts
        df                   (DataFrame)  — the full processed vendor DataFrame
    Returns:
        ChatResult(reply, updated_df)
    """

    # ── Intent classification ─────────────────────────────────────────────────

    INTENT_PROMPT: str = (
        "Classify the following user message as either READ or WRITE.\n\n"
        "READ: the user is asking a question or wants to see data.\n"
        "WRITE: the user wants to update, change, set, or fix a value.\n\n"
        "Reply with exactly one word: READ or WRITE."
    )

    # ── READ: code generation ─────────────────────────────────────────────────

    READ_CODE_GEN_PROMPT: str = (
        "You are a pandas code generator. A pandas DataFrame called `df` is available.\n\n"
        "DATAFRAME COLUMNS:\n{columns}\n\n"
        "SAMPLE DATA (first 3 rows — for column name and format reference ONLY):\n"
        "{sample_rows}\n\n"
        "ALL BUSINESS PARTNER IDs IN THE DATASET:\n{supplier_ids}\n\n"
        "RULES — follow strictly:\n"
        "1. Return ONLY a single valid Python expression. No imports. No assignments. No markdown. No explanation.\n"
        "2. The expression must use the variable `df`.\n"
        "3. For single-value lookups: use .values[0] — e.g. df[df['Business Partner']=='BP001']['Name'].values[0]\n"
        "4. For lists or tables: return a filtered DataFrame or Series.\n"
        "5. For counts: use len() or .value_counts().\n"
        "6. Column names are case-sensitive. Use exact column names from the list above.\n"
        "7. The sample data shows only 3 rows. The full dataset has many more rows — always query `df` directly.\n"
        "8. ONLY return CANNOT_ANSWER if the question asks about a column that does not exist in the column list above.\n"
        "   Never return CANNOT_ANSWER just because a Business Partner ID is not visible in the sample rows.\n"
    )

    # ── WRITE: code generation ────────────────────────────────────────────────

    WRITE_CODE_GEN_PROMPT: str = (
        "You are a pandas code generator for DATA UPDATES. A pandas DataFrame called `df` is available.\n\n"
        "DATAFRAME COLUMNS:\n{columns}\n\n"
        "ALL BUSINESS PARTNER IDs IN THE DATASET:\n{supplier_ids}\n\n"
        "RULES — follow strictly:\n"
        "1. Generate a single Python statement that updates df in-place. No imports. No markdown. No explanation.\n"
        "2. Use df.loc to target the exact row and column.\n"
        "   Example: df.loc[df['Business Partner'] == 'BP087', 'GDPR'] = 'GDPR-2026-06'\n"
        "3. Only update columns that exist in the column list above.\n"
        "4. Only update rows where Business Partner matches exactly as listed above.\n"
        "5. Do not generate any other statements.\n"
        "6. If the update cannot be performed because the column does not exist, return exactly: CANNOT_UPDATE\n"
    )

    # ── Result formatting ─────────────────────────────────────────────────────

    FORMAT_SYSTEM_PROMPT: str = (
        "You are a helpful vendor data analyst. "
        "The user asked a question and a Python pandas query was executed against the real dataset. "
        "Convert the raw query result below into a clear, concise natural language answer.\n\n"
        "RULES:\n"
        "1. Be factual. Only use information present in the raw result.\n"
        "2. Do not invent or assume any data not shown in the result.\n"
        "3. If the result is empty, say no matching records were found.\n"
        "4. Keep the answer concise. Use bullet points for multiple records.\n"
    )

    CONFIRM_UPDATE_PROMPT: str = (
        "You are a helpful vendor data analyst. "
        "The user requested a data update and it was successfully applied to the dataset. "
        "Write a short, friendly confirmation message (1-2 sentences) telling the user what was changed.\n\n"
        "RULES:\n"
        "1. Be specific — mention the Business Partner ID, field, and new value from the user's request.\n"
        "2. If the Status of the vendor changed as a result, mention the new Status.\n"
        "3. Do not invent information not present in the updated row provided.\n"
    )

    # ── Public API ────────────────────────────────────────────────────────────

    def run(
        self,
        user_message: str,
        conversation_history: list[dict],
        df: pd.DataFrame,
    ) -> ChatResult:
        intent = self._classify_intent(user_message)
        if intent == "WRITE":
            return self._handle_write(user_message, df)
        return self._handle_read(user_message, conversation_history, df)

    # ── READ path ─────────────────────────────────────────────────────────────

    def _handle_read(
        self,
        user_message: str,
        conversation_history: list[dict],
        df: pd.DataFrame,
    ) -> ChatResult:
        code = self._generate_read_code(user_message, df)

        if code.strip().upper().startswith("CANNOT_ANSWER"):
            return ChatResult(
                reply="I couldn't find relevant data in this dataset to answer that question.",
                updated_df=None,
            )

        try:
            query_result = eval(code, {"__builtins__": {}, "df": df, "pd": pd})  # noqa: S307
        except IndexError:
            return ChatResult(reply="No records were found matching your query.", updated_df=None)
        except KeyError as exc:
            return ChatResult(reply=f"The column {exc} doesn't exist in this dataset.", updated_df=None)
        except Exception:
            return ChatResult(reply="I wasn't able to compute that. Try rephrasing your question.", updated_df=None)

        reply = self._format_result(user_message, query_result, conversation_history)
        return ChatResult(reply=reply, updated_df=None)

    # ── WRITE path ────────────────────────────────────────────────────────────

    def _handle_write(self, user_message: str, df: pd.DataFrame) -> ChatResult:
        code = self._generate_write_code(user_message, df)

        if code.strip().upper().startswith("CANNOT_UPDATE"):
            return ChatResult(
                reply="I couldn't perform that update. Please check the column name and Business Partner ID.",
                updated_df=None,
            )

        df_copy = df.copy()
        try:
            exec(code, {"__builtins__": {}, "df": df_copy, "pd": pd})  # noqa: S102
        except KeyError as exc:
            return ChatResult(reply=f"Column {exc} doesn't exist in this dataset.", updated_df=None)
        except Exception:
            return ChatResult(reply="I wasn't able to perform that update. Try rephrasing.", updated_df=None)

        # Verify something actually changed
        if df_copy.equals(df):
            return ChatResult(
                reply="No matching vendor was found for that update. Please check the Business Partner ID.",
                updated_df=None,
            )

        # Capture which rows changed BEFORE recompute_status touches Status/Reason
        changed_indices = self._find_changed_rows(df, df_copy)

        df_copy = self._recompute_status(df_copy)
        self._stamp_audit_fields(df_copy, changed_indices)
        reply = self._confirm_update(user_message, df_copy)
        return ChatResult(reply=reply, updated_df=df_copy)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _classify_intent(self, user_message: str) -> str:
        """Returns 'WRITE' or 'READ'. Defaults to READ on any error."""
        try:
            from gen_ai_hub.proxy.native.openai import chat  # noqa: PLC0415

            response = chat.completions.create(
                model_name=MODEL_NAME,
                messages=[
                    {"role": "system", "content": self.INTENT_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=5,
                temperature=0,
            )
            result = response.choices[0].message.content.strip().upper()
            return "WRITE" if result == "WRITE" else "READ"
        except Exception:
            return "READ"

    def _generate_read_code(self, user_message: str, df: pd.DataFrame) -> str:
        columns = "\n".join(f"  - {c}" for c in df.columns.tolist())
        sample_rows = df.head(3).to_string(index=False)
        supplier_ids = ", ".join(df["Business Partner"].astype(str).tolist()) if "Business Partner" in df.columns else "N/A"

        system_prompt = self.READ_CODE_GEN_PROMPT.format(
            columns=columns, sample_rows=sample_rows, supplier_ids=supplier_ids
        )
        try:
            from gen_ai_hub.proxy.native.openai import chat  # noqa: PLC0415

            response = chat.completions.create(
                model_name=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=200,
                temperature=0,
            )
            code = response.choices[0].message.content.strip()
            return self._strip_fences(code)
        except Exception:
            return "CANNOT_ANSWER"

    def _generate_write_code(self, user_message: str, df: pd.DataFrame) -> str:
        columns = "\n".join(f"  - {c}" for c in df.columns.tolist())
        supplier_ids = ", ".join(df["Business Partner"].astype(str).tolist()) if "Business Partner" in df.columns else "N/A"

        system_prompt = self.WRITE_CODE_GEN_PROMPT.format(
            columns=columns, supplier_ids=supplier_ids
        )
        try:
            from gen_ai_hub.proxy.native.openai import chat  # noqa: PLC0415

            response = chat.completions.create(
                model_name=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=200,
                temperature=0,
            )
            code = response.choices[0].message.content.strip()
            return self._strip_fences(code)
        except Exception:
            return "CANNOT_UPDATE"

    def _recompute_status(self, df: pd.DataFrame) -> pd.DataFrame:
        """Recompute Status and Reason for every row based on GDPR/ECCN presence."""
        def is_missing(v) -> bool:
            return pd.isna(v) or (isinstance(v, str) and v.strip() == "")

        for i, row in df.iterrows():
            g = is_missing(row.get("GDPR"))
            e = is_missing(row.get("ECCN"))
            if not g and not e:
                df.at[i, "Status"] = "ACTIVE"
                df.at[i, "Reason"] = ""
            elif g and e:
                df.at[i, "Status"] = "INACTIVE"
                df.at[i, "Reason"] = "Both missing"
            elif g:
                df.at[i, "Status"] = "PENDING"
                df.at[i, "Reason"] = "Missing GDPR"
            else:
                df.at[i, "Status"] = "PENDING"
                df.at[i, "Reason"] = "Missing ECCN"
        return df

    def _find_changed_rows(self, original_df: pd.DataFrame, updated_df: pd.DataFrame) -> list:
        """Return index labels of rows that differ between original and updated df.
        Uses fillna to treat NaN==NaN as equal."""
        sentinel = "__NA__"
        orig_filled = original_df.fillna(sentinel)
        upd_filled = updated_df.fillna(sentinel)
        changed_mask = ~upd_filled.eq(orig_filled).all(axis=1)
        return updated_df.index[changed_mask].tolist()

    def _stamp_audit_fields(self, updated_df: pd.DataFrame, changed_indices: list) -> None:
        """Set Modify Date and Last Modified By on the specified rows."""
        import datetime
        if not changed_indices:
            return
        today = datetime.date.today().strftime("%d%m%Y")

        # Build a case-insensitive + whitespace-normalised map of actual column names
        col_map = {c.strip().lower(): c for c in updated_df.columns}
        modify_col = col_map.get("modify date")
        modified_by_col = col_map.get("last modified by")

        # Cast both audit columns to object dtype so strings can be assigned
        for col in filter(None, [modify_col, modified_by_col]):
            updated_df[col] = updated_df[col].astype(object)

        for i in changed_indices:
            if modify_col:
                updated_df.at[i, modify_col] = today
            if modified_by_col:
                updated_df.at[i, modified_by_col] = "I12345"

    def _confirm_update(self, user_message: str, df: pd.DataFrame) -> str:
        """Format a confirmation message for a successful update."""
        # Extract the updated row for context — find rows where Status/Reason may have changed
        context = df.to_string(index=False) if len(df) <= 5 else df.head(5).to_string(index=False)
        user_content = f"User's update request: {user_message}\n\nUpdated dataset (relevant rows):\n{context}"
        try:
            from gen_ai_hub.proxy.native.openai import chat  # noqa: PLC0415

            response = chat.completions.create(
                model_name=MODEL_NAME,
                messages=[
                    {"role": "system", "content": self.CONFIRM_UPDATE_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=150,
                temperature=0,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "Update applied successfully."

    def _format_result(
        self,
        user_message: str,
        query_result: object,
        conversation_history: list[dict],
    ) -> str:
        if isinstance(query_result, (pd.DataFrame, pd.Series)):
            result_str = query_result.to_string(index=False)
        else:
            result_str = str(query_result)

        user_content = f"User question: {user_message}\n\nRaw query result:\n{result_str}"
        try:
            from gen_ai_hub.proxy.native.openai import chat  # noqa: PLC0415

            messages = [{"role": "system", "content": self.FORMAT_SYSTEM_PROMPT}]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_content})

            response = chat.completions.create(
                model_name=MODEL_NAME,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=0,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return result_str

    @staticmethod
    def _strip_fences(code: str) -> str:
        """Remove markdown code fences if the model wraps output in them."""
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(l for l in lines if not l.startswith("```")).strip()
        return code
